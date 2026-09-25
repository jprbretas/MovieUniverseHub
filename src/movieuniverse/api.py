"""Montagem da API (FastAPI): cria o objeto `app`, regista as rotas e serve o frontend.

Equivalente C#: a parte do Program.cs entre o builder.Build() e os app.MapControllers().
Este módulo NÃO arranca servidor nenhum; quem o arranca é o __main__.py (via uvicorn).
Por isso os testes podem importar o `app` daqui sem ligar nada.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from movieuniverse.config import get_settings
from movieuniverse.db import criar_tabelas
from movieuniverse.dependencias import obter_cliente_tmdb
from movieuniverse.rotas import filmes
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
    """Código que corre ao arrancar (antes do yield) e ao desligar (depois do yield)."""
    criar_tabelas()  # ≈ context.Database.EnsureCreated() no arranque de uma app .NET
    yield
    if obter_cliente_tmdb.cache_info().currsize:  # se o cliente chegou a ser criado...
        obter_cliente_tmdb().fechar()             # ...fecha as ligações HTTP


app = FastAPI(
    title="MovieUniverse Hub",
    description="Pesquisar filmes (API TMDB), criar playlists e dar notas.",
    version="0.1.0",
    lifespan=ciclo_de_vida,
)

# --- Rotas -------------------------------------------------------------------
app.include_router(filmes.router)  # ≈ app.MapControllers()


@app.get("/api/health", tags=["sistema"])
def health() -> dict[str, object]:
    """Indica se a API está viva e se o token da TMDB foi configurado."""
    settings = get_settings()
    return {"status": "ok", "tmdb_configurada": settings.tmdb_configurada}


# --- Erros da TMDB -> respostas HTTP ------------------------------------------
# ≈ um exception filter / UseExceptionHandler do ASP.NET: as rotas limitam-se a lançar
# as nossas exceções e este mapa decide o código HTTP. O corpo segue o formato habitual
# do FastAPI: {"detail": "mensagem"}.
CODIGOS_HTTP = {
    FilmeNaoEncontrado: 404,  # o filme não existe
    TokenInvalido: 500,       # problema de configuração do nosso lado (.env)
    LimitePedidos: 503,       # a TMDB pediu para abrandar
    TMDBIndisponivel: 503,    # sem rede, timeout ou erro da TMDB
}


@app.exception_handler(ErroTMDB)
async def tratar_erro_tmdb(pedido: Request, erro: ErroTMDB) -> JSONResponse:
    codigo = CODIGOS_HTTP.get(type(erro), 502)  # 502 = resposta inesperada da TMDB
    return JSONResponse(status_code=codigo, content={"detail": str(erro)})


# --- Frontend -----------------------------------------------------------------
# Tem de ficar no FIM: o mount em "/" apanha tudo o que as rotas /api/... não apanharam.
# html=True faz com que "/" devolva o index.html.
app.mount("/", StaticFiles(directory=PASTA_STATIC, html=True), name="static")
