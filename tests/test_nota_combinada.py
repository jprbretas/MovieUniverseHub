"""Testes da nota combinada: os casos que o enunciado exige e os limites da regra.

A função é pura, por isso estes testes não precisam de base de dados nem de rede.
"""
import pytest

from movieuniverse.nota_combinada import NOTA_NEUTRA, calcular_nota_combinada

# Os dois filmes do exemplo do enunciado.
FILME_A = {"media_tmdb": 8.9, "votos_tmdb": 12}      # média mais alta, mas só 12 votos
FILME_B = {"media_tmdb": 8.4, "votos_tmdb": 30_000}  # média um pouco mais baixa, 30 000 votos


# --- Os casos do enunciado --------------------------------------------------------

def test_8_9_com_12_votos_fica_abaixo_de_8_4_com_30000_votos():
    a = calcular_nota_combinada(**FILME_A, media_app=None, votos_app=0)
    b = calcular_nota_combinada(**FILME_B, media_app=None, votos_app=0)

    assert a.valor < b.valor


def test_tres_utilizadores_a_dar_10_nao_mudam_a_ordem():
    a = calcular_nota_combinada(**FILME_A, media_app=10, votos_app=3)
    b = calcular_nota_combinada(**FILME_B, media_app=None, votos_app=0)

    assert a.valor < b.valor
    assert a.num_votos == 15  # 12 da TMDB + 3 da aplicação


def test_filme_sem_votos_nao_tem_nota_combinada():
    resultado = calcular_nota_combinada(media_tmdb=0, votos_tmdb=0, media_app=None, votos_app=0)

    assert resultado.valor is None
    assert resultado.texto == "informação insuficiente"
    assert "Informação insuficiente" in resultado.explicacao


# --- Comportamento da regra -------------------------------------------------------

def test_com_muitos_votos_a_nota_fica_perto_da_media_real():
    b = calcular_nota_combinada(**FILME_B, media_app=None, votos_app=0)

    assert b.valor == pytest.approx(8.4, abs=0.01)


def test_com_poucos_votos_a_nota_aproxima_se_da_nota_neutra():
    a = calcular_nota_combinada(**FILME_A, media_app=None, votos_app=0)

    assert abs(a.valor - NOTA_NEUTRA) < abs(8.9 - NOTA_NEUTRA)  # foi puxada para 6,5
    assert a.peso_media_real < 0.15


def test_filme_so_com_notas_da_aplicacao_tambem_tem_nota():
    resultado = calcular_nota_combinada(media_tmdb=0, votos_tmdb=0, media_app=9, votos_app=2)

    assert resultado.valor is not None
    assert NOTA_NEUTRA < resultado.valor < 9


@pytest.mark.parametrize("media", [0, 10])
def test_a_nota_fica_sempre_entre_0_e_10(media):
    resultado = calcular_nota_combinada(media_tmdb=media, votos_tmdb=1_000_000, media_app=None, votos_app=0)

    assert 0 <= resultado.valor <= 10


def test_texto_e_explicacao_indicam_os_votos():
    b = calcular_nota_combinada(**FILME_B, media_app=10, votos_app=3)

    assert b.texto == "8,4 · 30 003 votos"
    assert "30 000 da TMDB" in b.explicacao and "3 de utilizadores" in b.explicacao


def test_votos_negativos_dao_erro():
    with pytest.raises(ValueError):
        calcular_nota_combinada(media_tmdb=8, votos_tmdb=-1, media_app=None, votos_app=0)
