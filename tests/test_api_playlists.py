"""Testes dos endpoints de utilizadores, playlists e notas (base de dados em memória).

O `api` vem do conftest.py. Os filmes 603 e 27205 existem na TMDB falsa.
"""
import pytest


@pytest.fixture
def api_com_filmes(api, tmdb_falsa, json_tmdb):
    tmdb_falsa.responder("/movie/603", json_tmdb("filme_603.json"))
    tmdb_falsa.responder("/movie/27205", json_tmdb("filme_27205.json"))
    return api


def entrar(api, nome="ana") -> int:
    return api.post("/api/utilizadores", json={"nome": nome}).json()["id"]


def criar_playlist(api, utilizador_id, nome="Ficção científica") -> int:
    resposta = api.post(f"/api/utilizadores/{utilizador_id}/playlists", json={"nome": nome})
    assert resposta.status_code == 201
    return resposta.json()["id"]


# --- Utilizadores ------------------------------------------------------------------

def test_entrar_duas_vezes_com_o_mesmo_nome_devolve_o_mesmo_utilizador(api):
    primeiro = api.post("/api/utilizadores", json={"nome": "ana"}).json()
    segundo = api.post("/api/utilizadores", json={"nome": "  Ana "}).json()

    assert segundo["id"] == primeiro["id"]
    assert [u["nome"] for u in api.get("/api/utilizadores").json()] == ["ana"]


def test_nome_vazio_e_recusado(api):
    assert api.post("/api/utilizadores", json={"nome": "   "}).status_code == 422


# --- Playlists -----------------------------------------------------------------------

def test_adicionar_o_mesmo_filme_duas_vezes_nao_duplica(api_com_filmes):
    api = api_com_filmes
    playlist = criar_playlist(api, entrar(api))

    api.put(f"/api/playlists/{playlist}/filmes/27205")
    api.put(f"/api/playlists/{playlist}/filmes/603")
    resposta = api.put(f"/api/playlists/{playlist}/filmes/27205")

    assert resposta.status_code == 200
    assert resposta.json()["tmdb_ids"] == [27205, 603]  # pela ordem em que entraram


def test_detalhe_da_playlist_traz_os_dados_dos_filmes(api_com_filmes):
    api = api_com_filmes
    playlist = criar_playlist(api, entrar(api))
    api.put(f"/api/playlists/{playlist}/filmes/603")

    detalhe = api.get(f"/api/playlists/{playlist}").json()

    assert detalhe["dono"] == "ana"
    assert detalhe["filmes"][0]["filme"]["tmdb_id"] == 603
    assert detalhe["filmes"][0]["filme"]["nota_tmdb_texto"]


def test_remover_filme_da_playlist(api_com_filmes):
    api = api_com_filmes
    playlist = criar_playlist(api, entrar(api))
    api.put(f"/api/playlists/{playlist}/filmes/603")

    resposta = api.delete(f"/api/playlists/{playlist}/filmes/603")

    assert resposta.json()["tmdb_ids"] == []


def test_playlist_apagada_desaparece(api):
    ana = entrar(api)
    playlist = criar_playlist(api, ana)

    assert api.delete(f"/api/playlists/{playlist}").status_code == 204
    assert api.get(f"/api/utilizadores/{ana}/playlists").json() == []
    assert api.get(f"/api/playlists/{playlist}").status_code == 404


def test_filme_inexistente_nao_entra_na_playlist(api):
    playlist = criar_playlist(api, entrar(api))  # a TMDB falsa responde 404 a filmes não configurados

    assert api.put(f"/api/playlists/{playlist}/filmes/999999").status_code == 404


# --- Notas -----------------------------------------------------------------------

def test_dar_nota_e_alterar_depois_fica_uma_so_nota(api_com_filmes):
    api = api_com_filmes
    ana = entrar(api)

    api.put(f"/api/utilizadores/{ana}/notas/603", json={"estrelas": 6})
    api.put(f"/api/utilizadores/{ana}/notas/603", json={"estrelas": 9})

    notas = api.get("/api/filmes/603/notas").json()
    assert notas["num_notas"] == 1
    assert notas["notas"][0]["estrelas"] == 9


def test_media_das_notas_dos_utilizadores(api_com_filmes):
    api = api_com_filmes
    for nome, estrelas in [("ana", 8), ("bruno", 10), ("carla", 6)]:
        api.put(f"/api/utilizadores/{entrar(api, nome)}/notas/603", json={"estrelas": estrelas})

    notas = api.get("/api/filmes/603/notas").json()

    assert notas["num_notas"] == 3
    assert notas["media"] == 8.0


def test_notas_do_filme_trazem_a_nota_combinada(api_com_filmes, json_tmdb):
    api = api_com_filmes
    api.put(f"/api/utilizadores/{entrar(api)}/notas/603", json={"estrelas": 10})
    votos_tmdb = json_tmdb("filme_603.json")["vote_count"]

    combinada = api.get("/api/filmes/603/notas").json()["nota_combinada"]

    assert combinada["num_votos"] == votos_tmdb + 1
    assert combinada["votos_app"] == 1
    assert 0 < combinada["valor"] <= 10
    assert combinada["texto"] and combinada["explicacao"]


@pytest.mark.parametrize("estrelas", [0, 11])
def test_nota_fora_de_1_a_10_e_recusada(api_com_filmes, estrelas):
    ana = entrar(api_com_filmes)

    resposta = api_com_filmes.put(f"/api/utilizadores/{ana}/notas/603", json={"estrelas": estrelas})

    assert resposta.status_code == 422


def test_utilizador_inexistente_da_404(api):
    assert api.get("/api/utilizadores/999/playlists").status_code == 404
