"""Montagem da API: cria o `app`, regista as rotas e os erros e serve o frontend.

Não arranca nenhum servidor (isso é feito no __main__.py, com o uvicorn).
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from movieuniverse.config import get_settings
from movieuniverse.db import criar_tabelas
from movieuniverse.dependencias import obter_cliente_tmdb
from movieuniverse.rotas import filmes, playlists, utilizadores
from movieuniverse.servicos import NaoEncontrado
from movieuniverse.tmdb import (
    ErroTMDB,
    FilmeNaoEncontrado,
    LimitePedidos,
    TMDBIndisponivel,
    TokenInvalido,
)

PASTA_STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Cria as tabelas ao arrancar e fecha o cliente da TMDB ao desligar."""
    criar_tabelas()
    yield
    if obter_cliente_tmdb.cache_info().currsize:  # só se o cliente chegou a ser criado
        obter_cliente_tmdb().fechar()


app = FastAPI(
    title="MovieUniverse Hub",
    description="Pesquisar filmes (API TMDB), criar playlists e dar notas.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

app.include_router(filmes.router)
app.include_router(utilizadores.router)
app.include_router(playlists.router)


@app.get("/api/health", tags=["sistema"])
def health() -> dict[str, object]:
    """Indica se a API está viva e se o token da TMDB foi configurado."""
    settings = get_settings()
    return {"status": "ok", "tmdb_configurada": settings.tmdb_configurada}


# As rotas só lançam exceções; aqui decide-se o código HTTP. Corpo: {"detail": "mensagem"}.
CODIGOS_HTTP = {
    FilmeNaoEncontrado: 404,
    TokenInvalido: 500,       # problema de configuração do nosso lado (.env)
    LimitePedidos: 503,
    TMDBIndisponivel: 503,
}


@app.exception_handler(ErroTMDB)
async def tratar_erro_tmdb(pedido: Request, erro: ErroTMDB) -> JSONResponse:
    codigo = CODIGOS_HTTP.get(type(erro), 502)  # 502 = resposta inesperada da TMDB
    return JSONResponse(status_code=codigo, content={"detail": str(erro)})


@app.exception_handler(NaoEncontrado)
async def tratar_nao_encontrado(pedido: Request, erro: NaoEncontrado) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(erro)})


# Tem de ficar no fim: o mount em "/" apanha tudo o que as rotas /api/... não apanharam.
app.mount("/", StaticFiles(directory=PASTA_STATIC, html=True), name="static")
