"""Testes do ClienteTMDB contra uma TMDB falsa (sem internet, sem gastar pedidos).

Os parâmetros `cliente` e `tmdb_falsa` vêm das @pytest.fixture do conftest.py.
"""
import httpx2
import pytest

from movieuniverse.tmdb import (
    ClienteTMDB,
    ErroTMDB,
    FilmeNaoEncontrado,
    LimitePedidos,
    TMDBIndisponivel,
    TokenInvalido,
)

# --- Pesquisa ----------------------------------------------------------------


def test_pesquisar_envia_parametros_certos_e_devolve_pagina(cliente, tmdb_falsa, json_tmdb):
    tmdb_falsa.responder("/search/movie", json_tmdb("pesquisa_inception.json"))

    pagina = cliente.pesquisar("  Inception  ")

    pedido = tmdb_falsa.pedidos[0]
    assert pedido.url.params["query"] == "Inception"  # sem os espaços das pontas
    assert pedido.url.params["language"] == "pt-PT"
    assert pedido.url.params["page"] == "1"
    assert pedido.headers["Authorization"] == "Bearer token-de-teste"
    assert 27205 in [f.tmdb_id for f in pagina.filmes]


def test_pesquisar_titulo_vazio_nao_faz_pedido(cliente, tmdb_falsa):
    pagina = cliente.pesquisar("   ")

    assert pagina.filmes == []
    assert tmdb_falsa.pedidos == []


@pytest.mark.parametrize("pagina", [0, -1, 501])
def test_pesquisar_pagina_fora_dos_limites_da_erro(cliente, pagina):
    with pytest.raises(ValueError):
        cliente.pesquisar("Matrix", pagina=pagina)


# --- Detalhe -----------------------------------------------------------------


def test_detalhe_com_sinopse_faz_um_so_pedido(cliente, tmdb_falsa, json_tmdb):
    tmdb_falsa.responder("/movie/27205", json_tmdb("filme_27205.json"))

    filme = cliente.detalhe(27205)

    assert filme.tmdb_id == 27205
    assert len(tmdb_falsa.pedidos) == 1


def test_detalhe_sem_sinopse_em_pt_usa_a_inglesa(cliente, tmdb_falsa):
    base = {"id": 7, "title": "Título PT", "genres": [{"id": 1, "name": "Drama"}]}
    tmdb_falsa.responder("/movie/7", {**base, "overview": ""}, lingua="pt-PT")
    tmdb_falsa.responder("/movie/7", {**base, "overview": "English overview"}, lingua="en-US")

    filme = cliente.detalhe(7)

    assert filme.sinopse == "English overview"
    assert filme.titulo == "Título PT"          # o resto continua em português
    assert filme.generos[0].nome == "Drama"
    assert [p.url.params["language"] for p in tmdb_falsa.pedidos] == ["pt-PT", "en-US"]


# --- Erros -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "exececao"),
    [
        (401, TokenInvalido),
        (404, FilmeNaoEncontrado),
        (429, LimitePedidos),
        (500, TMDBIndisponivel),
        (503, TMDBIndisponivel),
        (418, ErroTMDB),
    ],
)
def test_erros_http_viram_as_nossas_excecoes(cliente, tmdb_falsa, status, exececao):
    tmdb_falsa.responder("/movie/1", status=status)

    with pytest.raises(exececao):
        cliente.detalhe(1)


def test_todas_as_excecoes_herdam_de_erro_tmdb():
    for exececao in (TokenInvalido, FilmeNaoEncontrado, LimitePedidos, TMDBIndisponivel):
        assert issubclass(exececao, ErroTMDB)


def test_limite_de_pedidos_indica_quanto_esperar(cliente, tmdb_falsa):
    tmdb_falsa.responder("/movie/1", status=429, headers={"Retry-After": "3"})

    with pytest.raises(LimitePedidos, match="3 segundos"):
        cliente.detalhe(1)


@pytest.mark.parametrize(
    "erro_de_rede",
    [httpx2.ConnectTimeout("timeout"), httpx2.ConnectError("sem rede")],
)
def test_falhas_de_rede_viram_tmdb_indisponivel(cliente, tmdb_falsa, erro_de_rede):
    tmdb_falsa.falhar("/movie/1", erro_de_rede)

    with pytest.raises(TMDBIndisponivel):
        cliente.detalhe(1)


def test_cliente_sem_token_nao_e_criado():
    with pytest.raises(TokenInvalido):
        ClienteTMDB("")
