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

        if registo is None:
            registo = FilmeCache(tmdb_id=tmdb_id)
            self.sessao.add(registo)
        registo.titulo = filme.titulo
        registo.media_votos = filme.media_votos
        registo.num_votos = filme.num_votos
        registo.dados_json = filme.model_dump_json()  # objeto -> texto JSON
        registo.atualizado_em = self.relogio()
        self.sessao.commit()
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

        if registo is None:
            registo = PesquisaCache(chave=chave)
            self.sessao.add(registo)
        registo.dados_json = resultado.model_dump_json()
        registo.atualizado_em = self.relogio()
        self.sessao.commit()
        return resultado

    # --- Auxiliares -----------------------------------------------------------

    def _ainda_valido(self, atualizado_em: datetime) -> bool:
        # O SQLite devolve as datas sem fuso; sabemos que foram gravadas em UTC.
        if atualizado_em.tzinfo is None:
            atualizado_em = atualizado_em.replace(tzinfo=timezone.utc)
        return self.relogio() - atualizado_em < self.validade
