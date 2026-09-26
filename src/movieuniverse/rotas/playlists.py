"""Rotas das playlists: listar, comparar duas, ver uma com os filmes, apagar, e
adicionar/remover filmes (a ★)."""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from movieuniverse import servicos
from movieuniverse.comparacao import ComparacaoPlaylists
from movieuniverse.dependencias import CatalogoDep, SessaoDep
from movieuniverse.esquemas import FilmeNaPlaylist, PlaylistDetalhe, PlaylistResumo, em_utc
from movieuniverse.tmdb import ErroTMDB

router = APIRouter(prefix="/api/playlists", tags=["playlists"])

PlaylistId = Annotated[int, Path(gt=0)]
TmdbId = Annotated[int, Path(gt=0, description="Id do filme na TMDB")]
NAO_ENCONTRADA = {404: {"description": "A playlist (ou o filme) não existe."}}


@router.get("")
def listar_playlists(sessao: SessaoDep) -> list[PlaylistResumo]:
    """Todas as playlists (sem as apagadas), de todos os utilizadores."""
    return [PlaylistResumo.de(p) for p in servicos.listar_playlists(sessao)]


# ATENÇÃO À ORDEM: esta rota tem de vir antes de "/{playlist_id}". O FastAPI experimenta as
# rotas pela ordem em que são registadas, e "comparar" seria lido como um playlist_id.
@router.get("/comparar", responses=NAO_ENCONTRADA)
def comparar_playlists(
    a: Annotated[int, Query(gt=0, description="Id da 1.ª playlist")],
    b: Annotated[int, Query(gt=0, description="Id da 2.ª playlist")],
    sessao: SessaoDep,
    catalogo: CatalogoDep,
) -> ComparacaoPlaylists:
    """Compara duas playlists: qual tem o melhor rating (média das notas combinadas dos filmes),
    o número de filmes, o melhor filme de cada uma, os filmes em comum e os que só estão numa."""
    if a == b:
        raise HTTPException(status_code=422, detail="Escolhe duas playlists diferentes para comparar.")
    return servicos.comparar(sessao, catalogo, a, b)


@router.get("/{playlist_id}", responses=NAO_ENCONTRADA)
def detalhe_playlist(playlist_id: PlaylistId, sessao: SessaoDep, catalogo: CatalogoDep) -> PlaylistDetalhe:
    """A playlist com os dados de cada filme (vindos da cache ou da TMDB)."""
    playlist = servicos.obter_playlist(sessao, playlist_id)

    filmes = []
    for item in playlist.filmes:
        try:
            filme = catalogo.detalhe(item.tmdb_id)
        except ErroTMDB:
            filme = None  # um filme indisponível não impede de ver o resto da playlist
        filmes.append(FilmeNaPlaylist(tmdb_id=item.tmdb_id, ordem=item.ordem, filme=filme))

    return PlaylistDetalhe(
        id=playlist.id,
        nome=playlist.nome,
        dono=playlist.utilizador.nome,
        criada_em=em_utc(playlist.criada_em),
        filmes=filmes,
    )


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NAO_ENCONTRADA)
def apagar_playlist(playlist_id: PlaylistId, sessao: SessaoDep) -> None:
    """Apaga a playlist (fica marcada como apagada e deixa de aparecer)."""
    servicos.apagar_playlist(sessao, playlist_id)


@router.put("/{playlist_id}/filmes/{tmdb_id}", responses=NAO_ENCONTRADA)
def adicionar_filme(
    playlist_id: PlaylistId, tmdb_id: TmdbId, sessao: SessaoDep, catalogo: CatalogoDep
) -> PlaylistResumo:
    """Adiciona o filme ao fim da playlist. Repetir o pedido não o duplica."""
    servicos.obter_playlist(sessao, playlist_id)  # 404 antes de gastar um pedido à TMDB
    catalogo.detalhe(tmdb_id)  # confirma que o filme existe (404 se não) e guarda-o na cache
    return PlaylistResumo.de(servicos.adicionar_filme(sessao, playlist_id, tmdb_id))


@router.delete("/{playlist_id}/filmes/{tmdb_id}", responses=NAO_ENCONTRADA)
def remover_filme(playlist_id: PlaylistId, tmdb_id: TmdbId, sessao: SessaoDep) -> PlaylistResumo:
    """Tira o filme da playlist."""
    return PlaylistResumo.de(servicos.remover_filme(sessao, playlist_id, tmdb_id))
