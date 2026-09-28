"""Esquemas da API: o formato do JSON que entra e sai dos endpoints.

Estão separados das entidades para a API e a base de dados poderem mudar uma sem a outra.
Os métodos `de(...)` convertem uma entidade no esquema correspondente.
"""
from datetime import date, datetime, timezone
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from movieuniverse.entidades import Nota, Playlist, Utilizador
from movieuniverse.nota_combinada import NotaCombinada
from movieuniverse.tmdb import FilmeResumo


def em_utc(momento: datetime) -> datetime:
    """Marca como UTC uma data lida do SQLite (que não guarda o fuso), para o JSON levar "+00:00"."""
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


NomeUtilizador = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
NomePlaylist = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


# --- Utilizadores ----------------------------------------------------------------

class UtilizadorEntrada(BaseModel):
    nome: NomeUtilizador


class UtilizadorSaida(BaseModel):
    id: int
    nome: str

    @classmethod
    def de(cls, utilizador: Utilizador) -> "UtilizadorSaida":
        return cls(id=utilizador.id, nome=utilizador.nome)


# --- Playlists -------------------------------------------------------------------

class PlaylistEntrada(BaseModel):
    nome: NomePlaylist


class PlaylistResumo(BaseModel):
    """Uma playlist sem os dados dos filmes (só os ids), para listas e para a ★."""

    id: int
    nome: str
    dono: str
    tmdb_ids: list[int] = Field(description="Ids dos filmes, pela ordem da playlist")
    criada_em: datetime

    @classmethod
    def de(cls, playlist: Playlist) -> "PlaylistResumo":
        return cls(
            id=playlist.id,
            nome=playlist.nome,
            dono=playlist.utilizador.nome,
            tmdb_ids=[f.tmdb_id for f in playlist.filmes],  # já vêm ordenados (order_by)
            criada_em=em_utc(playlist.criada_em),
        )


class FilmeNaPlaylist(BaseModel):
    tmdb_id: int
    ordem: int
    filme: FilmeResumo | None = Field(
        description="Dados do filme; null se a TMDB não respondeu e o filme não está na cache"
    )


class PlaylistDetalhe(BaseModel):
    """Uma playlist com os dados de cada filme (título, cartaz, nota), para a página dela."""

    id: int
    nome: str
    dono: str
    criada_em: datetime
    filmes: list[FilmeNaPlaylist]


# --- Notas -----------------------------------------------------------------------

class NotaEntrada(BaseModel):
    estrelas: int = Field(ge=1, le=10, description="Nota de 1 a 10")


class NotaSaida(BaseModel):
    utilizador: str
    tmdb_id: int
    estrelas: int
    data: date

    @classmethod
    def de(cls, nota: Nota) -> "NotaSaida":
        return cls(
            utilizador=nota.utilizador.nome,
            tmdb_id=nota.tmdb_id,
            estrelas=nota.estrelas,
            data=nota.data,
        )


class NotasDoFilme(BaseModel):
    """As notas dos utilizadores da aplicação para um filme e a nota combinada com a TMDB."""

    tmdb_id: int
    num_notas: int
    media: float | None = Field(description="Média das notas dos utilizadores; null se ninguém deu nota")
    notas: list[NotaSaida]
    nota_combinada: NotaCombinada
