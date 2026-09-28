"""Testes do servidor MCP com um cliente MCP verdadeiro, ligado em memória ao servidor.

O servidor usa a base de dados em memória, com o seed importado, e a TMDB falsa.
"""
import pytest
from mcp import Client
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from movieuniverse.entidades import Nota, Playlist, PlaylistFilme, Utilizador
from movieuniverse.importar import importar_seed
from movieuniverse.servidor_mcp import criar_servidor
from movieuniverse.tmdb import ClienteTMDB

pytestmark = pytest.mark.anyio  # o cliente MCP é assíncrono

FERRAMENTAS = {
    "pesquisar_filmes", "ficha_filme", "listar_utilizadores",
    "listar_playlists", "ver_playlist", "comparar_playlists",
}

# Filmes das playlists do seed usadas nos testes (pl-01 "Ficção científica" e pl-08 "Maratona sci-fi").
FILMES_DO_SEED = (27205, 603, 157336, 78, 438631, 329865, 152601)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def filme_falso(tmdb_id: int) -> dict:
    """Uma resposta mínima da TMDB para /movie/{id}, com o id certo."""
    return {
        "id": tmdb_id, "title": f"Filme {tmdb_id}", "release_date": "2000-01-01",
        "vote_average": 7.5, "vote_count": 1000, "genres": [{"id": 878, "name": "Ficção científica"}],
        "overview": "Sinopse.", "runtime": 120,
    }


@pytest.fixture
def servidor(sessao, engine_da_sessao, cliente, tmdb_falsa):
    importar_seed(sessao)
    for tmdb_id in FILMES_DO_SEED:
        tmdb_falsa.responder(f"/movie/{tmdb_id}", filme_falso(tmdb_id))
    return criar_servidor(fabrica_sessao=sessionmaker(bind=engine_da_sessao), obter_tmdb=lambda: cliente)


async def chamar(servidor, ferramenta: str, **argumentos):
    async with Client(servidor) as ia:
        return await ia.call_tool(ferramenta, argumentos)


async def id_da_playlist(servidor, nome: str) -> int:
    resultado = await chamar(servidor, "listar_playlists")
    return next(p["id"] for p in resultado.structured_content["result"] if p["nome"] == nome)


async def test_todas_as_ferramentas_sao_so_de_leitura(servidor):
    async with Client(servidor) as ia:
        ferramentas = (await ia.list_tools()).tools

    assert {f.name for f in ferramentas} == FERRAMENTAS
    assert all(f.annotations.read_only_hint for f in ferramentas)
    assert all(f.description for f in ferramentas)


async def test_pesquisar_filmes_devolve_o_tmdb_id_e_a_nota_com_votos(servidor, tmdb_falsa, json_tmdb):
    tmdb_falsa.responder("/search/movie", json_tmdb("pesquisa_matrix.json"))

    resultado = await chamar(servidor, "pesquisar_filmes", titulo="Matrix")

    assert not resultado.is_error
    primeiro = resultado.structured_content["filmes"][0]
    assert primeiro["tmdb_id"] > 0
    assert "votos" in primeiro["nota_tmdb"] or primeiro["nota_tmdb"] == "sem votos"


async def test_ficha_traz_a_nota_combinada_e_as_notas_dos_utilizadores(servidor):
    resultado = await chamar(servidor, "ficha_filme", tmdb_id=27205)

    ficha = resultado.structured_content
    assert ficha["nota_combinada"]["num_votos"] == 1003  # 1000 da TMDB + 3 da aplicação
    assert ficha["nota_combinada"]["explicacao"]
    assert {(n["utilizador"], n["estrelas"]) for n in ficha["notas_dos_utilizadores"]} == {
        ("ana", 9), ("bruno", 7), ("carla", 6)
    }


async def test_listar_playlists_de_um_utilizador_sem_distinguir_maiusculas(servidor):
    resultado = await chamar(servidor, "listar_playlists", utilizador="Ana")

    playlists = resultado.structured_content["result"]
    assert {p["nome"] for p in playlists} == {"Ficção científica", "Para rever num domingo", "Realizadores que sigo"}
    assert all(p["dono"] == "ana" for p in playlists)


async def test_utilizador_desconhecido_da_erro_com_a_lista_de_nomes(servidor):
    resultado = await chamar(servidor, "listar_playlists", utilizador="zé")

    assert resultado.is_error
    assert "ana, bruno, carla" in resultado.content[0].text


async def test_comparar_playlists_do_seed(servidor):
    a = await id_da_playlist(servidor, "Ficção científica")
    b = await id_da_playlist(servidor, "Maratona sci-fi")

    resultado = await chamar(servidor, "comparar_playlists", playlist_a=a, playlist_b=b)

    comparacao = resultado.structured_content
    assert len(comparacao["em_comum"]) == 3  # 27205, 157336 e 78
    assert comparacao["vencedora"] in {"Ficção científica", "Maratona sci-fi", "empate"}
    assert comparacao["a"]["num_filmes"] == 5


async def test_comparar_a_mesma_playlist_e_recusado(servidor):
    resultado = await chamar(servidor, "comparar_playlists", playlist_a=1, playlist_b=1)

    assert resultado.is_error
    assert "duas playlists diferentes" in resultado.content[0].text


async def test_playlist_inexistente_da_uma_mensagem_que_a_ia_percebe(servidor):
    resultado = await chamar(servidor, "ver_playlist", playlist_id=999)

    assert resultado.is_error
    assert "Não existe nenhuma playlist com id 999" in resultado.content[0].text


async def test_sem_token_so_as_ferramentas_da_tmdb_falham(sessao, engine_da_sessao):
    importar_seed(sessao)
    servidor = criar_servidor(fabrica_sessao=sessionmaker(bind=engine_da_sessao), obter_tmdb=lambda: ClienteTMDB(""))

    pesquisa = await chamar(servidor, "pesquisar_filmes", titulo="Matrix")
    playlists = await chamar(servidor, "listar_playlists")

    assert pesquisa.is_error and "TMDB_API_TOKEN" in pesquisa.content[0].text
    assert not playlists.is_error and len(playlists.structured_content["result"]) == 8


async def test_as_ferramentas_nao_alteram_os_dados(servidor, sessao):
    def contar():
        return [sessao.scalar(select(func.count()).select_from(t)) for t in (Utilizador, Playlist, PlaylistFilme, Nota)]

    antes = contar()
    a = await id_da_playlist(servidor, "Ficção científica")
    for ferramenta, argumentos in [
        ("listar_utilizadores", {}), ("listar_playlists", {}), ("ficha_filme", {"tmdb_id": 603}),
        ("ver_playlist", {"playlist_id": a}), ("comparar_playlists", {"playlist_a": a, "playlist_b": a + 1}),
    ]:
        await chamar(servidor, ferramenta, **argumentos)
    sessao.expire_all()

    assert contar() == antes
