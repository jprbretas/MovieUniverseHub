"""Rotas dos filmes: pesquisa e detalhe (≈ um FilmesController em ASP.NET).

As funções são "finas": validam a entrada, chamam o Catálogo e devolvem o modelo.
Os erros da TMDB (FilmeNaoEncontrado, TMDBIndisponivel...) NÃO são tratados aqui:
sobem até aos exception handlers do api.py, que os convertem em respostas HTTP.
"""
from typing import Annotated

from fastapi import APIRouter, Path, Query

from movieuniverse.dependencias import CatalogoDep
from movieuniverse.tmdb import PAGINA_MAXIMA, FilmeDetalhe, PaginaPesquisa

router = APIRouter(prefix="/api/filmes", tags=["filmes"])

# Documentação dos erros possíveis, para aparecerem no Swagger.
ERROS_TMDB = {
    503: {"description": "A TMDB não está disponível ou recusou demasiados pedidos."},
    500: {"description": "O token da TMDB está em falta ou é inválido (configuração do .env)."},
}


@router.get("", responses=ERROS_TMDB)
def pesquisar_filmes(
    catalogo: CatalogoDep,
    titulo: Annotated[str, Query(min_length=1, max_length=200, description="Título ou parte do título")],
    pagina: Annotated[int, Query(ge=1, le=PAGINA_MAXIMA, description="Página de resultados (20 por página)")] = 1,
) -> PaginaPesquisa:
    """Pesquisa filmes por título na TMDB (com cache)."""
    return catalogo.pesquisar(titulo, pagina)


@router.get(
    "/{tmdb_id}",
    responses={404: {"description": "Não existe nenhum filme com esse id."}, **ERROS_TMDB},
)
def detalhe_filme(
    catalogo: CatalogoDep,
    tmdb_id: Annotated[int, Path(gt=0, description="Id do filme na TMDB (ex.: 603)")],
) -> FilmeDetalhe:
    """Ficha completa de um filme: sinopse, géneros, duração, poster e nota da TMDB."""
    return catalogo.detalhe(tmdb_id)
