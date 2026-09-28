"""Tabelas da base de dados.

As restrições (chave primária composta, UNIQUE, CHECK) garantem as regras do enunciado
na própria base de dados, mesmo que algum código se engane.

As playlists e as notas guardam só o `tmdb_id`; os dados dos filmes ficam nas tabelas de
cache, no fim do ficheiro.

O SQLite não guarda o fuso horário: as datas são gravadas em UTC e lidas sem fuso.
"""
from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from movieuniverse.db import Base


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Utilizador(Base):
    __tablename__ = "utilizadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    # NOCASE: "Ana" e "ana" são o mesmo nome para o UNIQUE e para as pesquisas.
    nome: Mapped[str] = mapped_column(String(50, collation="NOCASE"), unique=True)
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    playlists: Mapped[list["Playlist"]] = relationship(back_populates="utilizador")
    notas: Mapped[list["Nota"]] = relationship(back_populates="utilizador")


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    utilizador_id: Mapped[int] = mapped_column(ForeignKey("utilizadores.id"))
    apagada: Mapped[bool] = mapped_column(default=False)  # soft delete, como no seed
    # Id externo: o do seed ("pl-01") ou o dado pela exportação ("app-..."). A importação
    # usa-o para reconhecer o que já existe. NULL nas playlists criadas na app e não exportadas.
    id_seed: Mapped[str | None] = mapped_column(String(20), unique=True)
    criada_em: Mapped[datetime] = mapped_column(default=agora)

    utilizador: Mapped[Utilizador] = relationship(back_populates="playlists")
    filmes: Mapped[list["PlaylistFilme"]] = relationship(
        back_populates="playlist",
        order_by="PlaylistFilme.ordem",
        cascade="all, delete-orphan",  # tirar um filme da lista apaga a linha
    )


class PlaylistFilme(Base):
    """Um filme dentro de uma playlist."""

    __tablename__ = "playlist_filmes"

    # Chave primária composta: o mesmo filme não pode estar duas vezes na mesma playlist.
    playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.id"), primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(primary_key=True)
    ordem: Mapped[int]

    playlist: Mapped[Playlist] = relationship(back_populates="filmes")


class Nota(Base):
    """A nota (1 a 10) que um utilizador dá a um filme."""

    __tablename__ = "notas"
    __table_args__ = (
        UniqueConstraint("utilizador_id", "tmdb_id", name="uma_nota_por_utilizador_e_filme"),
        CheckConstraint("estrelas BETWEEN 1 AND 10", name="estrelas_de_1_a_10"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    utilizador_id: Mapped[int] = mapped_column(ForeignKey("utilizadores.id"))
    tmdb_id: Mapped[int] = mapped_column(index=True)  # as notas são procuradas por filme
    estrelas: Mapped[int]
    data: Mapped[date] = mapped_column(default=lambda: agora().date())

    utilizador: Mapped[Utilizador] = relationship(back_populates="notas")


# --- Cache das respostas da TMDB (ver catalogo.py) ---------------------------------

class FilmeCache(Base):
    """Ficha de um filme (FilmeDetalhe) guardada para não a pedir de novo à TMDB."""

    __tablename__ = "filmes_cache"

    tmdb_id: Mapped[int] = mapped_column(primary_key=True)
    # Alguns campos também em colunas próprias, para se poder consultar sem abrir o JSON.
    titulo: Mapped[str] = mapped_column(String(300))
    media_votos: Mapped[float]
    num_votos: Mapped[int]
    dados_json: Mapped[str] = mapped_column(Text)
    atualizado_em: Mapped[datetime]


class PesquisaCache(Base):
    """Uma página de resultados de pesquisa, identificada por língua + título + página."""

    __tablename__ = "pesquisas_cache"

    chave: Mapped[str] = mapped_column(String(300), primary_key=True)  # ex.: "pt-PT|matrix|1"
    dados_json: Mapped[str] = mapped_column(Text)
    atualizado_em: Mapped[datetime]
