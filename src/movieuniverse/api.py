"""Montagem da API (FastAPI): cria o objeto `app`, regista as rotas e serve o frontend.

Equivalente C#: a parte do Program.cs entre o builder.Build() e os app.MapGet(...).
Este módulo NÃO arranca servidor nenhum; quem o arranca é o __main__.py (via uvicorn).
Por isso os testes podem importar o `app` daqui sem ligar nada.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from movieuniverse.config import get_settings
from movieuniverse.db import criar_tabelas

PASTA_STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Código que corre ao arrancar (antes do yield) e ao desligar (depois do yield)."""
    criar_tabelas()  # ≈ context.Database.EnsureCreated() no arranque de uma app .NET
    yield


app = FastAPI(
    title="MovieUniverse Hub",
    description="Pesquisar filmes (API TMDB), criar playlists e dar notas.",
    version="0.1.0",
    lifespan=ciclo_de_vida,
)


@app.get("/api/health", tags=["sistema"])
def health() -> dict[str, object]:
    """Indica se a API está viva e se o token da TMDB foi configurado."""
    settings = get_settings()
    return {"status": "ok", "tmdb_configurada": settings.tmdb_configurada}


# Tem de ficar no FIM: o mount em "/" apanha tudo o que as rotas /api/... não apanharam.
# html=True faz com que "/" devolva o index.html.
app.mount("/", StaticFiles(directory=PASTA_STATIC, html=True), name="static")
