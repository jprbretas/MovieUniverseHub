"""Testes da importação do seed, com o ficheiro verdadeiro (dados/seed_playlists.json).

Cada teste recebe uma base de dados nova em memória (`sessao`, do conftest.py).
"""
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from movieuniverse import servicos
from movieuniverse.entidades import Nota, Playlist, Utilizador
from movieuniverse.importar import importar_seed


def contar(sessao, entidade) -> int:
    return sessao.scalar(select(func.count()).select_from(entidade))


def playlist_seed(sessao, id_seed) -> Playlist:
    return sessao.scalar(select(Playlist).where(Playlist.id_seed == id_seed))


def test_importa_utilizadores_playlists_e_notas(sessao):
    relatorio = importar_seed(sessao)

    assert contar(sessao, Utilizador) == 3
    assert contar(sessao, Playlist) == 10
    assert contar(sessao, Nota) == 20
    assert relatorio.playlists_apagadas == 2


def test_correr_duas_vezes_nao_duplica(sessao):
    importar_seed(sessao)
    segundo = importar_seed(sessao)

    assert (contar(sessao, Utilizador), contar(sessao, Playlist), contar(sessao, Nota)) == (3, 10, 20)
    assert segundo.utilizadores_criados == segundo.playlists_criadas == segundo.notas_criadas == 0
    assert segundo.playlists_existentes == 10


def test_filme_repetido_fica_so_na_primeira_ocorrencia(sessao):
    relatorio = importar_seed(sessao)

    filmes = playlist_seed(sessao, "pl-01").filmes
    assert [f.tmdb_id for f in filmes].count(27205) == 1
    assert filmes[0].tmdb_id == 27205 and filmes[0].ordem == 1
    assert len(filmes) == 5
    assert any("27205" in aviso for aviso in relatorio.avisos)


def test_playlists_apagadas_sao_importadas_mas_nao_aparecem(sessao):
    importar_seed(sessao)

    assert playlist_seed(sessao, "pl-03").apagada is True
    ana = sessao.scalar(select(Utilizador).where(Utilizador.nome == "ana"))
    nomes = [p.nome for p in servicos.playlists_do_utilizador(sessao, ana.id)]
    assert "Rascunho antigo" not in nomes
    assert len(nomes) == 3  # pl-01, pl-02 e pl-04


def test_filmes_so_em_playlists_apagadas_sao_assinalados(sessao):
    relatorio = importar_seed(sessao)

    aviso = next(a for a in relatorio.avisos if "só existem em playlists apagadas" in a)
    for tmdb_id in ("289", "348", "550", "807"):
        assert tmdb_id in aviso


def test_notas_mantem_a_data_do_seed(sessao):
    importar_seed(sessao)

    datas = set(sessao.scalars(select(Nota.data)))
    assert {d.isoformat() for d in datas} == {"2026-09-01"}


def test_reimportar_nao_desfaz_alteracoes_feitas_na_app(sessao):
    importar_seed(sessao)
    ana = sessao.scalar(select(Utilizador).where(Utilizador.nome == "ana"))
    servicos.dar_nota(sessao, ana.id, 27205, 5)                       # a ana mudou a nota de 9 para 5
    servicos.remover_filme(sessao, playlist_seed(sessao, "pl-01").id, 603)  # e tirou o 603 da pl-01

    importar_seed(sessao)

    nota = sessao.scalar(select(Nota).where(Nota.utilizador_id == ana.id, Nota.tmdb_id == 27205))
    assert nota.estrelas == 5
    assert 603 not in [f.tmdb_id for f in playlist_seed(sessao, "pl-01").filmes]


def test_ficheiro_com_formato_errado_nao_importa_nada(sessao, tmp_path):
    ficheiro = tmp_path / "errado.json"
    ficheiro.write_text(json.dumps({"versao": "1.0", "utilizadores": [{"nome": "x"}]}), encoding="utf-8")

    with pytest.raises(ValidationError):
        importar_seed(sessao, ficheiro)
    assert contar(sessao, Utilizador) == 0
