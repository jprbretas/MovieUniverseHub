"""Peças partilhadas pelos testes (o pytest carrega este ficheiro automaticamente).

Atenção a duas palavras parecidas:
  - "fixtures" (pasta tests/fixtures/): FICHEIROS com dados de teste (os JSON reais da TMDB).
  - @pytest.fixture (abaixo): FUNÇÕES que preparam objetos para os testes. Um teste que
    declara um parâmetro com o mesmo nome recebe esse objeto automaticamente
    (≈ injeção de dependências no construtor de uma classe de testes xUnit).
"""
import json
from pathlib import Path

import httpx2
import pytest
from sqlalchemy.orm import Session

from movieuniverse.db import criar_engine, criar_tabelas
from movieuniverse.tmdb import ClienteTMDB

PASTA_FIXTURES = Path(__file__).parent / "fixtures" / "tmdb"


def carregar_json(nome: str) -> dict:
    """Lê um dos JSON reais guardados pelo scripts/explorar_tmdb.py."""
    return json.loads((PASTA_FIXTURES / nome).read_text(encoding="utf-8"))


class TMDBFalsa:
    """Imita a API da TMDB sem internet (≈ um HttpMessageHandler falso, ou um mock do Moq).

    Configura-se com `responder(...)` e, no fim, dá para ver que pedidos foram feitos
    em `self.pedidos`.
    """

    def __init__(self) -> None:
        self.pedidos: list[httpx2.Request] = []
        self._respostas: dict[tuple[str, str | None], httpx2.Response | Exception] = {}

    def responder(
        self,
        caminho: str,
        json: dict | None = None,
        status: int = 200,
        lingua: str | None = None,
        headers: dict | None = None,
    ) -> None:
        """Define o que devolver para um caminho (ex.: "/movie/603"), opcionalmente por língua."""
        self._respostas[(caminho, lingua)] = httpx2.Response(status, json=json or {}, headers=headers)

    def falhar(self, caminho: str, erro: Exception) -> None:
        """Simula uma falha de rede (timeout, sem ligação...) nesse caminho."""
        self._respostas[(caminho, None)] = erro

    def __call__(self, pedido: httpx2.Request) -> httpx2.Response:
        # __call__ faz com que o objeto possa ser chamado como uma função: tmdb_falsa(pedido)
        self.pedidos.append(pedido)
        caminho = pedido.url.path.removeprefix("/3")
        lingua = pedido.url.params.get("language")
        resposta = self._respostas.get((caminho, lingua))  # resposta específica desta língua...
        if resposta is None:
            resposta = self._respostas.get((caminho, None))  # ...ou a genérica do caminho
        if resposta is None:
            return httpx2.Response(404, json={"status_message": "não configurado no teste"})
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


@pytest.fixture
def json_tmdb():
    """Dá aos testes a função que lê os JSON reais: json_tmdb("filme_27205.json")."""
    return carregar_json


@pytest.fixture
def tmdb_falsa() -> TMDBFalsa:
    return TMDBFalsa()


@pytest.fixture
def cliente(tmdb_falsa: TMDBFalsa):
    """Um ClienteTMDB verdadeiro, mas ligado à TMDB falsa em vez da internet."""
    with ClienteTMDB("token-de-teste", transport=httpx2.MockTransport(tmdb_falsa)) as c:
        yield c  # o teste corre aqui; depois do yield, o `with` fecha o cliente (≈ Dispose)


@pytest.fixture
def sessao():
    """Uma base de dados SQLite nova, EM MEMÓRIA, para cada teste (não toca no ficheiro real).

    ≈ usar o provider InMemory/SQLite in-memory do EF Core nos testes.
    """
    engine = criar_engine("sqlite://")  # "sqlite://" sem caminho = base de dados em memória
    criar_tabelas(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()
