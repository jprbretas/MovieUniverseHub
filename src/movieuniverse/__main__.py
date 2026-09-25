"""Ponto de entrada: python -m movieuniverse [comando]

    python -m movieuniverse                  arranca a aplicação (≈ dotnet run)
    python -m movieuniverse importar-seed    importa dados/seed_playlists.json

Os "subcomandos" funcionam como os do dotnet (dotnet run, dotnet ef ...).
"""
import argparse
import sys
from pathlib import Path

import uvicorn
from pydantic import ValidationError

from movieuniverse.config import get_settings

PASTA_APP = Path(__file__).parent


def arrancar_servidor() -> None:
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


def importar(ficheiro: Path) -> int:
    # Imports aqui dentro: o servidor não precisa deles para arrancar.
    from movieuniverse.db import SessaoLocal, criar_tabelas
    from movieuniverse.importar import importar_seed

    try:
        criar_tabelas()
        with SessaoLocal() as sessao:
            relatorio = importar_seed(sessao, ficheiro)
    except FileNotFoundError:
        print(f"Ficheiro não encontrado: {ficheiro}")
        return 1
    except ValidationError as erro:
        print(f"O ficheiro {ficheiro} não tem o formato esperado:\n{erro}")
        return 1

    print(f"Importação de {ficheiro.name} concluída:")
    print(relatorio.texto())
    return 0


def main(argumentos: list[str] | None = None) -> int:
    from movieuniverse.importar import FICHEIRO_SEED

    parser = argparse.ArgumentParser(prog="python -m movieuniverse", description="MovieUniverse Hub")
    comandos = parser.add_subparsers(dest="comando")
    comandos.add_parser("servidor", help="arranca a aplicação (é o que acontece sem comando)")
    importar_cmd = comandos.add_parser("importar-seed", help="importa os dados de exemplo")
    importar_cmd.add_argument(
        "--ficheiro", type=Path, default=FICHEIRO_SEED, help="caminho do JSON (por omissão: dados/seed_playlists.json)"
    )
    args = parser.parse_args(argumentos)

    if args.comando == "importar-seed":
        return importar(args.ficheiro)
    arrancar_servidor()
    return 0


if __name__ == "__main__":
    sys.exit(main())
