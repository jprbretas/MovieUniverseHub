"""Testes da cache do catálogo (TMDB falsa + base de dados em memória, sem internet)."""
from datetime import datetime, timedelta, timezone

import httpx2
import pytest

from movieuniverse.catalogo import Catalogo
from movieuniverse.entidades import FilmeCache
from movieuniverse.tmdb import TMDBIndisponivel


class RelogioFalso:
    """Um "agora" controlado pelo teste, para simular a passagem do tempo."""

    def __init__(self) -> None:
        self.atual = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.atual

    def avancar(self, horas: int) -> None:
        self.atual += timedelta(hours=horas)


@pytest.fixture
def relogio() -> RelogioFalso:
    return RelogioFalso()


@pytest.fixture
def catalogo(sessao, cliente, relogio) -> Catalogo:
    return Catalogo(sessao, cliente, relogio=relogio)


def test_segundo_pedido_do_mesmo_filme_vem_da_cache(catalogo, tmdb_falsa, json_tmdb, sessao):
    tmdb_falsa.responder("/movie/27205", json_tmdb("filme_27205.json"))

    primeiro = catalogo.detalhe(27205)
    segundo = catalogo.detalhe(27205)

    assert len(tmdb_falsa.pedidos) == 1           # só o primeiro foi à TMDB
    assert segundo == primeiro                    # e a cópia é igual ao original
    guardado = sessao.get(FilmeCache, 27205)
    assert guardado.num_votos == primeiro.num_votos


def test_cache_expirada_volta_a_pedir_a_tmdb(catalogo, tmdb_falsa, json_tmdb, relogio):
    tmdb_falsa.responder("/movie/27205", json_tmdb("filme_27205.json"))
    catalogo.detalhe(27205)

    relogio.avancar(horas=25)  # passou mais de um dia
    catalogo.detalhe(27205)

    assert len(tmdb_falsa.pedidos) == 2


def test_tmdb_em_baixo_devolve_a_copia_antiga(catalogo, tmdb_falsa, json_tmdb, relogio):
    tmdb_falsa.responder("/movie/27205", json_tmdb("filme_27205.json"))
    original = catalogo.detalhe(27205)

    relogio.avancar(horas=25)
    tmdb_falsa.falhar("/movie/27205", httpx2.ConnectError("sem rede"))

    assert catalogo.detalhe(27205) == original


def test_tmdb_em_baixo_sem_copia_propaga_o_erro(catalogo, tmdb_falsa):
    tmdb_falsa.falhar("/movie/603", httpx2.ConnectError("sem rede"))

    with pytest.raises(TMDBIndisponivel):
        catalogo.detalhe(603)


def test_pesquisas_iguais_com_maiusculas_e_espacos_usam_a_mesma_cache(
    catalogo, tmdb_falsa, json_tmdb
):
    tmdb_falsa.responder("/search/movie", json_tmdb("pesquisa_matrix.json"))

    catalogo.pesquisar("Matrix")
    catalogo.pesquisar("  matrix ")

    assert len(tmdb_falsa.pedidos) == 1


def test_outro_pedido_a_gravar_o_mesmo_filme_ao_mesmo_tempo_nao_da_erro(tmp_path, json_tmdb, relogio):
    """Reproduz a race condition: enquanto este pedido espera pela TMDB, outro pedido
    (outra sessão) grava o mesmo filme na cache. Antes do upsert, isto dava
    "UNIQUE constraint failed"."""
    from sqlalchemy.orm import Session

    from movieuniverse.db import criar_engine, criar_tabelas
    from movieuniverse.tmdb import ClienteTMDB

    engine = criar_engine(f"sqlite:///{tmp_path / 'teste.db'}")  # ficheiro: ligações separadas
    criar_tabelas(engine)
    dados = json_tmdb("filme_27205.json")

    def tmdb_lenta(pedido):
        with Session(engine) as outro_pedido:
            outro_pedido.add(FilmeCache(tmdb_id=27205, titulo="versão do outro pedido", media_votos=1,
                                        num_votos=1, dados_json="{}", atualizado_em=relogio()))
            outro_pedido.commit()
        return httpx2.Response(200, json=dados)

    with Session(engine) as sessao, ClienteTMDB("t", transport=httpx2.MockTransport(tmdb_lenta)) as cliente:
        filme = Catalogo(sessao, cliente, relogio=relogio).detalhe(27205)
        assert filme.tmdb_id == 27205
        assert sessao.get(FilmeCache, 27205).titulo == filme.titulo  # ficou a versão mais recente
    engine.dispose()
