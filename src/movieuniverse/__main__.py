"""Permite arrancar a aplicação com: python -m movieuniverse

Equivalente C#: `dotnet run`. Lê o host e a porta da configuração e sobe o servidor.
"""
from pathlib import Path

import uvicorn

from movieuniverse.config import get_settings

PASTA_APP = Path(__file__).parent


def main() -> None:
    settings = get_settings()
    print(f"MovieUniverse Hub em http://{settings.host}:{settings.port}  (Swagger: /docs)")
    uvicorn.run(
        "movieuniverse.api:app",  # "módulo:variável"; o reload exige este formato em texto
        host=settings.host,
        port=settings.port,
        # reload: reinicia sozinho quando alteras um .py (≈ dotnet watch).
        # Só vigia o código da app, não o .venv.
        reload=settings.reload,
        reload_dirs=[str(PASTA_APP)] if settings.reload else None,
    )


if __name__ == "__main__":
    main()
