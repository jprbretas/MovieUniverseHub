"""Catálogo de filmes: a TMDB com uma cache na base de dados à frente.

Em cada pedido: se a cópia na cache tiver menos de 24 horas, usa-a sem ir à TMDB; senão,
pede à TMDB e atualiza a cache. Se a TMDB falhar (sem rede ou 429), devolve a cópia antiga,
se existir; se não existir, o erro segue para quem chamou.
"""
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy.dialects.sqlite import insert as insert_sqlite
from sqlalchemy.orm import Session

from movieuniverse.entidades import FilmeCache, PesquisaCache
from movieuniverse.tmdb import (
    ClienteTMDB,
    FilmeDetalhe,
    LimitePedidos,
    PaginaPesquisa,
    TMDBIndisponivel,
)

# As notas e os votos da TMDB mudam devagar: um dia equilibra dados frescos e poucos pedidos.
VALIDADE_CACHE = timedelta(hours=24)

# Erros em que vale a pena usar uma cópia antiga: a TMDB existe, mas agora não responde.
ERROS_TEMPORARIOS = (TMDBIndisponivel, LimitePedidos)


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class Catalogo:
    def __init__(
        self,
        sessao: Session,
        tmdb: ClienteTMDB,
        validade: timedelta = VALIDADE_CACHE,
        relogio: Callable[[], datetime] = agora_utc,
    ) -> None:
        # `relogio` devolve "agora"; os testes passam um relógio falso para simular o tempo a passar.
        self.sessao = sessao
        self.tmdb = tmdb
        self.validade = validade
        self.relogio = relogio

    def detalhe(self, tmdb_id: int) -> FilmeDetalhe:
        registo = self.sessao.get(FilmeCache, tmdb_id)
        if registo and self._ainda_valido(registo.atualizado_em):
            return FilmeDetalhe.model_validate_json(registo.dados_json)

        try:
            filme = self.tmdb.detalhe(tmdb_id)
        except ERROS_TEMPORARIOS:
            if registo:
                return FilmeDetalhe.model_validate_json(registo.dados_json)
            raise

        self._guardar(
            FilmeCache,
            chave={"tmdb_id": tmdb_id},
            valores={
                "titulo": filme.titulo,
                "media_votos": filme.media_votos,
                "num_votos": filme.num_votos,
                "dados_json": filme.model_dump_json(),
                "atualizado_em": self.relogio(),
            },
        )
        return filme

    def pesquisar(self, titulo: str, pagina: int = 1) -> PaginaPesquisa:
        if not titulo.strip():
            return self.tmdb.pesquisar(titulo, pagina)  # página vazia, sem pedido nem cache

        # " Matrix " e "matrix" são a mesma pesquisa.
        chave = f"{self.tmdb.lingua}|{titulo.strip().lower()}|{pagina}"
        registo = self.sessao.get(PesquisaCache, chave)
        if registo and self._ainda_valido(registo.atualizado_em):
            return PaginaPesquisa.model_validate_json(registo.dados_json)

        try:
            resultado = self.tmdb.pesquisar(titulo, pagina)
        except ERROS_TEMPORARIOS:
            if registo:
                return PaginaPesquisa.model_validate_json(registo.dados_json)
            raise

        self._guardar(
            PesquisaCache,
            chave={"chave": chave},
            valores={"dados_json": resultado.model_dump_json(), "atualizado_em": self.relogio()},
        )
        return resultado

    def _guardar(self, tabela, chave: dict, valores: dict) -> None:
        """Grava com um upsert (INSERT ... ON CONFLICT DO UPDATE), numa só instrução atómica.

        Com "ler e, se não existir, inserir", dois pedidos simultâneos ao mesmo filme (a ficha
        pede o filme e as notas em paralelo) faziam ambos o INSERT e o segundo falhava.
        """
        instrucao = (
            insert_sqlite(tabela)
            .values(**chave, **valores)
            .on_conflict_do_update(index_elements=list(chave), set_=valores)
        )
        self.sessao.execute(instrucao)
        self.sessao.commit()

    def _ainda_valido(self, atualizado_em: datetime) -> bool:
        # O SQLite devolve as datas sem fuso; foram gravadas em UTC.
        if atualizado_em.tzinfo is None:
            atualizado_em = atualizado_em.replace(tzinfo=timezone.utc)
        return self.relogio() - atualizado_em < self.validade
