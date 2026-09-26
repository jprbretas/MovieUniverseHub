"""Testes de segurança: tentativas de pôr dados inválidos ou "injetar" SQL.

Mostram a defesa em camadas:
  1. a API valida a entrada (Pydantic)            -> 422
  2. a base de dados valida outra vez (CHECK)      -> IntegrityError, mesmo contornando a API
  3. o SQL usa sempre parâmetros (SQLAlchemy)      -> texto com SQL é guardado como texto
"""
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from movieuniverse import servicos
from movieuniverse.entidades import Nota, PesquisaCache, Utilizador
from movieuniverse.importar import importar_seed

TABELAS = {"utilizadores", "playlists", "playlist_filmes", "notas", "filmes_cache", "pesquisas_cache"}


@pytest.fixture
def api_com_filme(api, tmdb_falsa, json_tmdb):
    tmdb_falsa.responder("/movie/603", json_tmdb("filme_603.json"))
    return api


def entrar(api, nome="ana") -> int:
    return api.post("/api/utilizadores", json={"nome": nome}).json()["id"]


@pytest.mark.parametrize("estrelas", [20, -5, 0, 11, 9.5, "10; DROP TABLE notas"])
def test_nota_fora_de_1_a_10_ou_que_nao_e_inteiro_e_recusada_pela_api(api_com_filme, sessao, estrelas):
    ana = entrar(api_com_filme)

    resposta = api_com_filme.put(f"/api/utilizadores/{ana}/notas/603", json={"estrelas": estrelas})

    assert resposta.status_code == 422
    assert sessao.scalar(select(func.count()).select_from(Nota)) == 0


def test_nota_20_e_recusada_pela_base_de_dados_mesmo_contornando_a_api(sessao):
    ana = servicos.entrar(sessao, "ana")

    with pytest.raises(IntegrityError, match="estrelas_de_1_a_10"):
        servicos.dar_nota(sessao, ana.id, 603, 20)


def test_sql_injection_no_nome_e_guardado_como_texto(api_com_filme, sessao, engine_da_sessao):
    nome_malicioso = "ana'; DROP TABLE notas; --"
    ana = entrar(api_com_filme)
    api_com_filme.put(f"/api/utilizadores/{ana}/notas/603", json={"estrelas": 8})

    resposta = api_com_filme.post("/api/utilizadores", json={"nome": nome_malicioso})

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == nome_malicioso                   # guardado tal e qual
    assert TABELAS <= set(inspect(engine_da_sessao).get_table_names())  # nenhuma tabela apagada
    assert sessao.scalar(select(func.count()).select_from(Nota)) == 1   # a nota continua lá


def test_sql_injection_na_pesquisa_nao_afeta_a_base_de_dados(api, tmdb_falsa, json_tmdb, sessao):
    tmdb_falsa.responder("/search/movie", json_tmdb("pesquisa_matrix.json"))
    texto_malicioso = "x' OR 1=1; DROP TABLE utilizadores; --"

    assert api.get("/api/filmes", params={"titulo": texto_malicioso}).status_code == 200
    chaves = list(sessao.scalars(select(PesquisaCache.chave)))
    assert chaves == [f"pt-PT|{texto_malicioso.lower()}|1"]  # a chave da cache é só texto
    assert sessao.scalar(select(func.count()).select_from(Utilizador)) == 0  # tabela intacta


def test_seed_com_nota_20_e_recusado_sem_importar_nada(sessao, tmp_path):
    ficheiro = tmp_path / "seed_malicioso.json"
    ficheiro.write_text(json.dumps({
        "versao": "1.0",
        "utilizadores": [{"nome": "ana"}],
        "playlists": [],
        "notas": [{"utilizador": "ana", "tmdb_id": 603, "estrelas": 20, "data": "2026-09-01"}],
    }), encoding="utf-8")

    with pytest.raises(ValidationError):
        importar_seed(sessao, ficheiro)
    assert sessao.scalar(select(func.count()).select_from(Utilizador)) == 0
