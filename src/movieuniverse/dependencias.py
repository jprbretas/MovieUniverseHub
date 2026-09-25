"""Dependências das rotas (injeção de dependências do FastAPI).

Equivalente C#: o registo de serviços no Program.cs (builder.Services.AddScoped<...>())
e a injeção no construtor dos controllers. No FastAPI, uma rota declara um parâmetro
com `Depends(funcao)` e o FastAPI chama essa função para obter o objeto.

    obter_sessao        -> uma sessão da base de dados por pedido   (≈ AddScoped<DbContext>)
    obter_cliente_tmdb  -> um único ClienteTMDB para a app toda      (≈ AddSingleton / HttpClient)
    obter_catalogo      -> Catálogo montado com os dois de cima      (≈ AddScoped<Catalogo>)

Nos testes trocamos o obter_catalogo por um falso com `app.dependency_overrides`
(≈ ConfigureTestServices no WebApplicationFactory).
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
    """Sempre a mesma instância: reaproveita as ligações HTTP entre pedidos."""
    return ClienteTMDB.da_config()


def obter_catalogo(
    sessao: Annotated[Session, Depends(obter_sessao)],
    tmdb: Annotated[ClienteTMDB, Depends(obter_cliente_tmdb)],
) -> Catalogo:
    return Catalogo(sessao, tmdb)


# Atalhos para as rotas: `catalogo: CatalogoDep` em vez de repetir o Depends(...).
# Dentro do mesmo pedido, o FastAPI reutiliza a mesma sessão em todo o lado
# (a da rota e a do Catálogo), tal como um serviço Scoped em .NET.
SessaoDep = Annotated[Session, Depends(obter_sessao)]
CatalogoDep = Annotated[Catalogo, Depends(obter_catalogo)]
