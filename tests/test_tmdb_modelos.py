"""Testes dos modelos da TMDB: conversão do JSON e texto da nota."""
import re

import pytest
from pydantic import ValidationError

from movieuniverse.tmdb import (
    URL_IMAGENS,
    FilmeDetalhe,
    FilmeResumo,
    PaginaPesquisa,
    formatar_nota_tmdb,
)

# --- Texto da nota -----------------------------------------------------------
# @pytest.mark.parametrize ≈ [Theory] + [InlineData(...)] do xUnit: o mesmo teste corre
# uma vez por cada linha da lista.


@pytest.mark.parametrize(
    ("media", "votos", "esperado"),
    [
        (7.8, 12340, "7,8 · 12 340 votos"),   # o exemplo do enunciado
        (8.374, 40258, "8,4 · 40 258 votos"),  # arredonda a uma casa decimal
        (9.0, 1, "9,0 · 1 voto"),              # singular
        (0.0, 0, "sem votos"),                 # sem votos -> nunca "0"
        (8.9, 0, "sem votos"),                 # média sem votos não conta
    ],
)
def test_formatar_nota_tmdb(media, votos, esperado):
    assert formatar_nota_tmdb(media, votos) == esperado


# --- Conversão das respostas reais da TMDB ------------------------------------


def test_detalhe_real_e_convertido(json_tmdb):
    filme = FilmeDetalhe.model_validate(json_tmdb("filme_27205.json"))

    assert filme.tmdb_id == 27205
    assert filme.titulo_original == "Inception"
    assert filme.ano == 2010
    assert filme.duracao_min == 148
    assert len(filme.generos) > 0 and all(g.nome for g in filme.generos)
    assert filme.sinopse != ""
    assert filme.poster_url.startswith(URL_IMAGENS)
    # O número de votos muda com o tempo, por isso verificamos só o formato.
    assert re.fullmatch(r"\d,\d · [\d ]+ votos", filme.nota_tmdb_texto)


def test_pesquisa_real_e_convertida(json_tmdb):
    pagina = PaginaPesquisa.model_validate(json_tmdb("pesquisa_inception.json"))

    assert pagina.pagina == 1
    assert 0 < len(pagina.filmes) <= 20
    assert 27205 in [f.tmdb_id for f in pagina.filmes]


def test_pesquisa_real_tem_filmes_sem_votos_e_sem_ano(json_tmdb):
    """Os dados reais têm casos-limite; o modelo tem de os aguentar sem rebentar."""
    pagina = PaginaPesquisa.model_validate(json_tmdb("pesquisa_inception.json"))

    assert any(f.nota_tmdb_texto == "sem votos" for f in pagina.filmes)
    assert any(f.ano is None for f in pagina.filmes)
    assert any(f.poster_url is None for f in pagina.filmes)


# --- Casos-limite construídos à mão ------------------------------------------


def test_valores_em_falta_da_tmdb_viram_desconhecidos():
    filme = FilmeDetalhe.model_validate(
        {"id": 1, "title": "X", "release_date": "", "runtime": 0, "overview": None, "poster_path": None}
    )

    assert filme.ano is None
    assert filme.duracao_min is None
    assert filme.sinopse == ""
    assert filme.poster_url is None
    assert filme.nota_tmdb_texto == "sem votos"


def test_campos_desconhecidos_sao_ignorados():
    filme = FilmeResumo.model_validate({"id": 1, "title": "X", "softcore": False, "campo_novo": 123})

    assert not hasattr(filme, "softcore")


def test_id_invalido_da_erro_de_validacao():
    # pytest.raises ≈ Assert.Throws<ValidationError>(...) do xUnit
    with pytest.raises(ValidationError):
        FilmeResumo.model_validate({"id": "abc", "title": "X"})
