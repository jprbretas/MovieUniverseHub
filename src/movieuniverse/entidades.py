"""Tabelas da base de dados (entidades do ORM).

Equivalente C#: as classes de entidade do Entity Framework. Cada classe é uma tabela e
cada atributo `Mapped[...]` é uma coluna. As `relationship` são as propriedades de
navegação (≈ `public List<Playlist> Playlists { get; set; }`).

As restrições (chave primária composta, UNIQUE, CHECK) garantem as regras do enunciado
na própria base de dados, mesmo que algum código se engane.

Os filmes em si NÃO têm tabela aqui: guardamos só o `tmdb_id`, que é a referência ao
filme na TMDB. Os dados do filme (título, notas...) vêm da TMDB e da cache (próxima parte).
"""
from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from movieuniverse.db import Base


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Utilizador(Base):
    __tablename__ = "utilizadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    # collation NOCASE: "Ana" e "ana" contam como o mesmo nome para o UNIQUE.
    nome: Mapped[str] = mapped_column(String(50, collation="NOCASE"), unique=True)
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    playlists: Mapped[list["Playlist"]] = relationship(back_populates="utilizador")
    notas: Mapped[list["Nota"]] = relationship(back_populates="utilizador")


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    utilizador_id: Mapped[int] = mapped_column(ForeignKey("utilizadores.id"))
    # "Apagar" só marca a playlist (soft delete), tal como no seed. Ela deixa de aparecer,
    # mas os dados não se perdem.
    apagada: Mapped[bool] = mapped_column(default=False)
    # O id que a playlist tem no seed ("pl-01"...). Serve para a importação reconhecer o
    # que já importou e não duplicar. `str | None` = coluna que aceita NULL.
    id_seed: Mapped[str | None] = mapped_column(String(20), unique=True)
    criada_em: Mapped[datetime] = mapped_column(default=agora)

    utilizador: Mapped[Utilizador] = relationship(back_populates="playlists")
    filmes: Mapped[list["PlaylistFilme"]] = relationship(
        back_populates="playlist",
        order_by="PlaylistFilme.ordem",   # já vêm ordenados
        cascade="all, delete-orphan",     # tirar da lista = apagar a linha
    )


class PlaylistFilme(Base):
    """Um filme dentro de uma playlist (tabela de ligação playlist <-> tmdb_id)."""

    __tablename__ = "playlist_filmes"

    # Chave primária COMPOSTA (playlist_id, tmdb_id): o mesmo filme não pode entrar duas
    # vezes na mesma playlist. É a regra por trás da armadilha do 27205 duplicado no seed.
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
    tmdb_id: Mapped[int] = mapped_column(index=True)  # índice: vamos juntar notas por filme
    estrelas: Mapped[int]
    data: Mapped[date] = mapped_column(default=lambda: agora().date())

    utilizador: Mapped[Utilizador] = relationship(back_populates="notas")
