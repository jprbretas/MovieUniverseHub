"""Catálogo de filmes: a TMDB com uma cache na base de dados à frente.

Fluxo de cada pedido:

    pedido ──► está na cache e ainda é válido? ──sim──► devolve da cache (0 pedidos à TMDB)
                          │ não
                          ▼
               pede à TMDB ──ok──► guarda na cache e devolve
                          │ falhou (sem rede / 429)
                          ▼
               há uma cópia antiga? ──sim──► devolve a cópia antiga (melhor do que nada)
                          │ não
                          ▼
                    lança o erro

Equivalente C#: um serviço que "decora" o cliente HTTP com cache (padrão Decorator),
como se faria com IMemoryCache/IDistributedCache à volta de um HttpClient tipado.
O ClienteTMDB continua a não saber nada de base de dados; só o Catálogo sabe.
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

# Quanto tempo uma resposta guardada é considerada atual. As notas e os votos da TMDB
# mudam devagar; um dia é um bom equilíbrio entre dados frescos e poucos pedidos.
VALIDADE_CACHE = timedelta(hours=24)

# Erros em que vale a pena usar uma cópia antiga: a TMDB está lá, mas agora não responde.
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
        # `relogio` é uma função que devolve "agora". Nos testes passamos um relógio falso
        # para simular que o tempo passou (≈ injetar o TimeProvider no .NET 8).
        self.sessao = sessao
        self.tmdb = tmdb
        self.validade = validade
        self.relogio = relogio

    # --- Detalhe de um filme ------------------------------------------------

    def detalhe(self, tmdb_id: int) -> FilmeDetalhe:
        registo = self.sessao.get(FilmeCache, tmdb_id)
        if registo and self._ainda_valido(registo.atualizado_em):
            return FilmeDetalhe.model_validate_json(registo.dados_json)

        try:
            filme = self.tmdb.detalhe(tmdb_id)
        except ERROS_TEMPORARIOS:
            if registo:
                return FilmeDetalhe.model_validate_json(registo.dados_json)
            raise  # sem cópia antiga: o erro segue para quem chamou

        self._guardar(
            FilmeCache,
            chave={"tmdb_id": tmdb_id},
            valores={
                "titulo": filme.titulo,
                "media_votos": filme.media_votos,
                "num_votos": filme.num_votos,
                "dados_json": filme.model_dump_json(),  # objeto -> texto JSON
                "atualizado_em": self.relogio(),
            },
        )
        return filme

    # --- Pesquisa -------------------------------------------------------------

    def pesquisar(self, titulo: str, pagina: int = 1) -> PaginaPesquisa:
        if not titulo.strip():
            return self.tmdb.pesquisar(titulo, pagina)  # página vazia, sem pedido nem cache

        # " Matrix " e "matrix" são a mesma pesquisa: normalizamos antes de montar a chave.
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

    # --- Auxiliares -----------------------------------------------------------

    def _guardar(self, tabela, chave: dict, valores: dict) -> None:
        """Grava na cache com um "upsert": INSERT ... ON CONFLICT DO UPDATE.

        Porquê não "ler, e se não existir fazer INSERT"? Porque dois pedidos ao mesmo tempo
        (a ficha pede o filme e as notas em paralelo) podiam ambos não encontrar o registo
        e ambos tentar o INSERT: o segundo falhava com "UNIQUE constraint failed".
        O upsert faz tudo numa só instrução atómica (≈ MERGE em SQL Server).
        """
        instrucao = (
            insert_sqlite(tabela)
            .values(**chave, **valores)
            .on_conflict_do_update(index_elements=list(chave), set_=valores)
        )
        self.sessao.execute(instrucao)
        self.sessao.commit()


    def _ainda_valido(self, atualizado_em: datetime) -> bool:
        # O SQLite devolve as datas sem fuso; sabemos que foram gravadas em UTC.
        if atualizado_em.tzinfo is None:
            atualizado_em = atualizado_em.replace(tzinfo=timezone.utc)
        return self.relogio() - atualizado_em < self.validade
