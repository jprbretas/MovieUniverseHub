"""Testes dos endpoints de filmes, ponta a ponta: HTTP -> rota -> Catálogo -> TMDB falsa.

O `api` vem do conftest.py: a app com a base de dados em memória e a TMDB falsa.
"""
import httpx2
import pytest


def test_pesquisa_devolve_filmes_com_nomes_em_portugues(api, tmdb_falsa, json_tmdb):
    tmdb_falsa.responder("/search/movie", json_tmdb("pesquisa_inception.json"))

    resposta = api.get("/api/filmes", params={"titulo": "Inception"})

    assert resposta.status_code == 200
    primeiro = resposta.json()["filmes"][0]
    assert primeiro["tmdb_id"] == 27205
    assert {"titulo", "ano", "poster_url", "nota_tmdb_texto"} <= primeiro.keys()


def test_detalhe_devolve_a_ficha_do_filme(api, tmdb_falsa, json_tmdb):
    tmdb_falsa.responder("/movie/27205", json_tmdb("filme_27205.json"))

    resposta = api.get("/api/filmes/27205")

    assert resposta.status_code == 200
    filme = resposta.json()
    assert filme["duracao_min"] == 148
    assert filme["generos"] and filme["sinopse"]


def test_filme_inexistente_da_404(api, tmdb_falsa):
    tmdb_falsa.responder("/movie/999999", status=404)

    resposta = api.get("/api/filmes/999999")

    assert resposta.status_code == 404
    assert "detail" in resposta.json()


def test_tmdb_em_baixo_da_503(api, tmdb_falsa):
    tmdb_falsa.falhar("/movie/603", httpx2.ConnectError("sem rede"))

    assert api.get("/api/filmes/603").status_code == 503


@pytest.mark.parametrize("url", ["/api/filmes?titulo=", "/api/filmes", "/api/filmes/0"])
def test_pedidos_invalidos_dao_422(api, url):
    # 422 = o FastAPI validou os parâmetros e recusou (≈ ModelState inválido -> 400 em ASP.NET)
    assert api.get(url).status_code == 422
