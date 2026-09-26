"""Testes da comparação de playlists (função pura: sem base de dados nem rede)."""
from movieuniverse.comparacao import FilmeAvaliado, comparar_playlists
from movieuniverse.nota_combinada import calcular_nota_combinada


def filme(tmdb_id: int, media_tmdb: float, votos: int = 10_000) -> FilmeAvaliado:
    """Um filme com a nota combinada calculada pela função verdadeira."""
    return FilmeAvaliado(
        tmdb_id=tmdb_id,
        titulo=f"Filme {tmdb_id}",
        nota_combinada=calcular_nota_combinada(media_tmdb, votos, None, 0),
    )


def playlist(playlist_id: int, *filmes: FilmeAvaliado):
    return (playlist_id, f"Playlist {playlist_id}", "ana", list(filmes))


def test_ganha_a_playlist_com_a_maior_media_de_nota_combinada():
    resultado = comparar_playlists(
        playlist(1, filme(10, 8.0), filme(11, 7.0)),
        playlist(2, filme(20, 6.0), filme(21, 6.5)),
    )

    assert resultado.vencedora == "a"
    assert resultado.a.media > resultado.b.media
    assert "Playlist 1" in resultado.explicacao


def test_filmes_sem_votos_ficam_de_fora_da_media_mas_sao_contados():
    sem_votos = filme(99, 0, votos=0)
    resultado = comparar_playlists(
        playlist(1, filme(10, 8.0), sem_votos),
        playlist(2, filme(20, 7.0)),
    )

    assert resultado.a.num_filmes == 2
    assert resultado.a.num_filmes_com_nota == 1
    assert resultado.a.media == filme(10, 8.0).nota_combinada.valor  # o filme sem votos não baixou a média
    assert "ficaram de fora" in resultado.explicacao


def test_medias_iguais_dao_empate():
    resultado = comparar_playlists(playlist(1, filme(10, 7.5)), playlist(2, filme(20, 7.5)))

    assert resultado.vencedora == "empate"
    assert resultado.diferenca == 0


def test_playlist_sem_filmes_com_nota_nao_tem_vencedora():
    resultado = comparar_playlists(playlist(1, filme(10, 8.0)), playlist(2, filme(99, 0, votos=0)))

    assert resultado.vencedora is None
    assert "Informação insuficiente" in resultado.explicacao


def test_extras_em_comum_so_numa_e_melhor_filme():
    comum, so_a, so_b = filme(1, 7.0), filme(2, 9.0), filme(3, 6.0)
    resultado = comparar_playlists(playlist(1, comum, so_a), playlist(2, comum, so_b))

    assert [f.tmdb_id for f in resultado.em_comum] == [1]
    assert [f.tmdb_id for f in resultado.a.so_nesta] == [2]
    assert [f.tmdb_id for f in resultado.b.so_nesta] == [3]
    assert resultado.a.melhor_filme.tmdb_id == 2
    assert resultado.b.melhor_filme.tmdb_id == 1
