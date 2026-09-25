"""Ligação à base de dados (SQLAlchemy + SQLite).

Equivalente C#: a configuração do DbContext do Entity Framework
(options.UseSqlite(...)) e o Database.EnsureCreated().

Três peças:
  - engine: sabe COMO ligar à base de dados (≈ a connection string + o provider).
  - SessaoLocal: fábrica de sessões; cada sessão é uma "unidade de trabalho" (≈ um DbContext).
  - Base: classe-mãe das tabelas (as entidades estão em entidades.py).
"""
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from movieuniverse.config import get_settings


class Base(DeclarativeBase):
    """Classe-mãe de todas as tabelas (≈ os DbSet<T> registados no DbContext)."""


def criar_engine(url: str) -> Engine:
    """Cria o engine. Para SQLite em ficheiro, garante que a pasta existe."""
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url)

    if url.startswith("sqlite"):
        # O SQLite IGNORA as chaves estrangeiras por omissão! Este "evento" corre a cada
        # nova ligação e liga a verificação (≈ um interceptor de ligação no EF Core).
        @event.listens_for(engine, "connect")
        def ligar_chaves_estrangeiras(ligacao_sqlite, _registo):
            cursor = ligacao_sqlite.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = criar_engine(get_settings().database_url)
SessaoLocal = sessionmaker(bind=engine)


def criar_tabelas(engine_alvo: Engine = engine) -> None:
    """Cria as tabelas que ainda não existem (≈ EnsureCreated; não apaga dados)."""
    from movieuniverse import entidades  # noqa: F401  (importar regista as tabelas na Base)

    Base.metadata.create_all(engine_alvo)


def obter_sessao() -> Iterator[Session]:
    """Uma sessão por pedido HTTP (≈ DbContext com tempo de vida Scoped).

    Vai ser usada no Passo 3 com o Depends() do FastAPI.
    """
    with SessaoLocal() as sessao:
        yield sessao
