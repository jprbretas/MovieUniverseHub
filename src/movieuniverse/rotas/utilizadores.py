"""Rotas dos utilizadores e do que lhes pertence: as suas playlists e as suas notas.

Como não há login (ver DECISIONS.md), o utilizador é identificado no próprio caminho:
/api/utilizadores/{utilizador_id}/playlists, /api/utilizadores/{utilizador_id}/notas/...
"""
from typing import Annotated

from fastapi import APIRouter, Path, status

from movieuniverse import servicos
from movieuniverse.dependencias import CatalogoDep, SessaoDep
from movieuniverse.esquemas import (
    NotaEntrada,
    NotaSaida,
    PlaylistEntrada,
    PlaylistResumo,
    UtilizadorEntrada,
    UtilizadorSaida,
)

router = APIRouter(prefix="/api/utilizadores", tags=["utilizadores"])

UtilizadorId = Annotated[int, Path(gt=0)]
TmdbId = Annotated[int, Path(gt=0, description="Id do filme na TMDB")]
NAO_ENCONTRADO = {404: {"description": "O utilizador (ou o filme) não existe."}}


@router.get("")
def listar_utilizadores(sessao: SessaoDep) -> list[UtilizadorSaida]:
    """Todos os utilizadores, por ordem alfabética."""
    return [UtilizadorSaida.de(u) for u in servicos.listar_utilizadores(sessao)]


@router.post("")
def entrar(dados: UtilizadorEntrada, sessao: SessaoDep) -> UtilizadorSaida:
    """Entra com um nome. Se ainda não existir, o utilizador é criado."""
    return UtilizadorSaida.de(servicos.entrar(sessao, dados.nome))


@router.get("/{utilizador_id}/playlists", responses=NAO_ENCONTRADO)
def playlists_do_utilizador(utilizador_id: UtilizadorId, sessao: SessaoDep) -> list[PlaylistResumo]:
    """As playlists do utilizador (sem as apagadas), com os ids dos filmes de cada uma."""
    return [PlaylistResumo.de(p) for p in servicos.playlists_do_utilizador(sessao, utilizador_id)]


@router.post("/{utilizador_id}/playlists", status_code=status.HTTP_201_CREATED, responses=NAO_ENCONTRADO)
def criar_playlist(
    utilizador_id: UtilizadorId, dados: PlaylistEntrada, sessao: SessaoDep
) -> PlaylistResumo:
    """Cria uma playlist vazia com o nome indicado."""
    return PlaylistResumo.de(servicos.criar_playlist(sessao, utilizador_id, dados.nome))


@router.put("/{utilizador_id}/notas/{tmdb_id}", responses=NAO_ENCONTRADO)
def dar_nota(
    utilizador_id: UtilizadorId,
    tmdb_id: TmdbId,
    dados: NotaEntrada,
    sessao: SessaoDep,
    catalogo: CatalogoDep,
) -> NotaSaida:
    """Dá (ou altera) a nota de 1 a 10 do utilizador a um filme. Só existe uma por filme."""
    servicos.obter_utilizador(sessao, utilizador_id)  # 404 antes de gastar um pedido à TMDB
    catalogo.detalhe(tmdb_id)  # confirma que o filme existe (404 se não) e guarda-o na cache
    return NotaSaida.de(servicos.dar_nota(sessao, utilizador_id, tmdb_id, dados.estrelas))


@router.delete("/{utilizador_id}/notas/{tmdb_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NAO_ENCONTRADO)
def remover_nota(utilizador_id: UtilizadorId, tmdb_id: TmdbId, sessao: SessaoDep) -> None:
    """Retira a nota do utilizador a este filme (se existir)."""
    servicos.remover_nota(sessao, utilizador_id, tmdb_id)
