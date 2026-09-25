"""Testes de fumo: a API arranca e a página inicial é servida.

Equivalente C#: testes xUnit com WebApplicationFactory. O TestClient chama a app
em memória, sem abrir nenhuma porta.
"""
import pytest
from fastapi.testclient import TestClient

from movieuniverse.api import app

client = TestClient(app)


def test_health_responde_ok():
    resposta = client.get("/api/health")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


def test_health_nunca_expoe_o_token():
    corpo = client.get("/api/health").json()

    # Só dizemos SE está configurado, nunca O QUÊ.
    assert set(corpo.keys()) == {"status", "tmdb_configurada"}
    assert isinstance(corpo["tmdb_configurada"], bool)


def test_pagina_inicial_e_servida():
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "MovieUniverse" in resposta.text


@pytest.mark.parametrize("caminho", ["/js/app.js", "/js/api.js", "/css/estilo.css"])
def test_ficheiros_do_frontend_sao_servidos(caminho):
    assert client.get(caminho).status_code == 200
