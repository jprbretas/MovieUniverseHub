"""Testes das regras que a própria base de dados garante (chaves e restrições).

O parâmetro `sessao` vem do conftest.py: uma base de dados nova em memória por teste.
"""
import pytest
from sqlalchemy.exc import IntegrityError

from movieuniverse.entidades import Nota, Playlist, PlaylistFilme, Utilizador


def criar_utilizador(sessao, nome="ana") -> Utilizador:
    utilizador = Utilizador(nome=nome)
    sessao.add(utilizador)
    sessao.flush()  # envia o INSERT já (≈ SaveChanges sem fechar a transação) e preenche o id
    return utilizador


def test_playlist_devolve_filmes_pela_ordem(sessao):
    ana = criar_utilizador(sessao)
    playlist = Playlist(nome="Ficção científica", utilizador=ana)
    playlist.filmes = [
        PlaylistFilme(tmdb_id=603, ordem=2),
        PlaylistFilme(tmdb_id=27205, ordem=1),
    ]
    sessao.add(playlist)
    sessao.commit()
    sessao.expire_all()  # obriga a reler da base de dados, em vez de usar o que está em memória

    relida = sessao.get(Playlist, playlist.id)
    assert [f.tmdb_id for f in relida.filmes] == [27205, 603]
    assert relida.apagada is False


def test_mesmo_filme_duas_vezes_na_mesma_playlist_e_rejeitado(sessao):
    ana = criar_utilizador(sessao)
    playlist = Playlist(nome="Duplicados", utilizador=ana)
    sessao.add(playlist)
    sessao.flush()
    sessao.add_all([
        PlaylistFilme(playlist_id=playlist.id, tmdb_id=27205, ordem=1),
        PlaylistFilme(playlist_id=playlist.id, tmdb_id=27205, ordem=6),
    ])

    with pytest.raises(IntegrityError):
        sessao.flush()


def test_so_uma_nota_por_utilizador_e_filme(sessao):
    ana = criar_utilizador(sessao)
    sessao.add_all([
        Nota(utilizador=ana, tmdb_id=27205, estrelas=9),
        Nota(utilizador=ana, tmdb_id=27205, estrelas=5),
    ])

    with pytest.raises(IntegrityError):
        sessao.flush()


@pytest.mark.parametrize("estrelas", [0, 11])
def test_estrelas_fora_de_1_a_10_sao_rejeitadas(sessao, estrelas):
    ana = criar_utilizador(sessao)
    sessao.add(Nota(utilizador=ana, tmdb_id=603, estrelas=estrelas))

    with pytest.raises(IntegrityError):
        sessao.flush()


def test_nome_de_utilizador_e_unico_sem_distinguir_maiusculas(sessao):
    criar_utilizador(sessao, "ana")

    with pytest.raises(IntegrityError):
        criar_utilizador(sessao, "Ana")


def test_chaves_estrangeiras_estao_ativas(sessao):
    # Sem o PRAGMA foreign_keys=ON do db.py, o SQLite aceitaria este utilizador inexistente.
    sessao.add(Nota(utilizador_id=999, tmdb_id=603, estrelas=7))

    with pytest.raises(IntegrityError):
        sessao.flush()
