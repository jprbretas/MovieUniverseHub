"""Dependências injetadas nas rotas com Depends().

    obter_sessao        -> uma sessão da base de dados por pedido
    obter_cliente_tmdb  -> um único ClienteTMDB para a aplicação toda
    obter_catalogo      -> o Catálogo, montado com os dois de cima

Os testes trocam-nas por versões falsas com `app.dependency_overrides`.
"""
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from movieuniverse.catalogo import Catalogo
from movieuniverse.db import obter_sessao
from movieuniverse.tmdb import ClienteTMDB


@lru_cache
def obter_cliente_tmdb() -> ClienteTMDB:
    """Sempre a mesma instância, para reaproveitar as ligações HTTP entre pedidos."""
    return ClienteTMDB.da_config()


def obter_catalogo(
    sessao: Annotated[Session, Depends(obter_sessao)],
    tmdb: Annotated[ClienteTMDB, Depends(obter_cliente_tmdb)],
) -> Catalogo:
    return Catalogo(sessao, tmdb)


# Dentro do mesmo pedido, o FastAPI reutiliza a mesma sessão (a da rota e a do Catálogo).
SessaoDep = Annotated[Session, Depends(obter_sessao)]
CatalogoDep = Annotated[Catalogo, Depends(obter_catalogo)]
