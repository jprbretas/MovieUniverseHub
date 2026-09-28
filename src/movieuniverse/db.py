"""Ligação à base de dados (SQLAlchemy + SQLite): o engine, a fábrica de sessões e a Base das tabelas."""
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from movieuniverse.config import get_settings


class Base(DeclarativeBase):
    """Classe-mãe de todas as tabelas (definidas em entidades.py)."""


def criar_engine(url: str) -> Engine:
    """Cria o engine. Para SQLite em ficheiro, garante que a pasta existe."""
    if url.startswith("sqlite:///") and not url.endswith(":memory:"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

    opcoes: dict = {}
    if url.startswith("sqlite"):
        # O FastAPI atende os pedidos em threads diferentes; cada sessão continua a ser de um só pedido.
        opcoes["connect_args"] = {"check_same_thread": False}
    if url in ("sqlite://", "sqlite:///:memory:"):
        # Em memória, cada ligação nova seria uma base vazia: o StaticPool reutiliza a mesma (testes).
        opcoes["poolclass"] = StaticPool

    engine = create_engine(url, **opcoes)

    if url.startswith("sqlite"):
        # O SQLite ignora as chaves estrangeiras por omissão: liga-as em cada nova ligação.
        @event.listens_for(engine, "connect")
        def ligar_chaves_estrangeiras(ligacao_sqlite, _registo):
            cursor = ligacao_sqlite.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = criar_engine(get_settings().database_url)
SessaoLocal = sessionmaker(bind=engine)


def criar_tabelas(engine_alvo: Engine = engine) -> None:
    """Cria as tabelas que ainda não existem (não altera nem apaga dados)."""
    from movieuniverse import entidades  # noqa: F401  (o import regista as tabelas na Base)

    Base.metadata.create_all(engine_alvo)


def obter_sessao() -> Iterator[Session]:
    """Uma sessão por pedido HTTP, fechada no fim (usada com o Depends() do FastAPI)."""
    with SessaoLocal() as sessao:
        yield sessao
