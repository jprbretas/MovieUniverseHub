"""Testes da exportação: o ficheiro tem o formato do seed e volta a entrar sem duplicar nada."""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from movieuniverse import servicos
from movieuniverse.db import criar_engine, criar_tabelas
from movieuniverse.entidades import Utilizador
from movieuniverse.exportar import exportar_dados, exportar_para_ficheiro
from movieuniverse.importar import FICHEIRO_SEED, importar_seed


def seed_com_uma_playlist_nova(sessao) -> None:
    """O seed e mais uma playlist criada "na aplicação" pela ana."""
    importar_seed(sessao)
    ana = sessao.scalar(select(Utilizador).where(Utilizador.nome == "ana"))
    nova = servicos.criar_playlist(sessao, ana.id, "Criada na app")
    servicos.adicionar_filme(sessao, nova.id, 603)


def test_exportar_depois_do_seed_devolve_os_mesmos_dados(sessao):
    importar_seed(sessao)
    seed = json.loads(FICHEIRO_SEED.read_text(encoding="utf-8"))

    dados = exportar_dados(sessao)

    assert [u.nome for u in dados.utilizadores] == ["ana", "bruno", "carla"]
    assert [p.id for p in dados.playlists] == [p["id"] for p in seed["playlists"]]
    assert {p.id for p in dados.playlists if p.apagada} == {"pl-03", "pl-07"}
    notas = {(n.utilizador, n.tmdb_id, n.estrelas) for n in dados.notas}
    assert notas == {(n["utilizador"], n["tmdb_id"], n["estrelas"]) for n in seed["notas"]}
    # A pl-01 sai sem o 27205 repetido (a importação já o tinha tirado).
    pl01 = next(p for p in dados.playlists if p.id == "pl-01")
    assert [f.tmdb_id for f in pl01.filmes].count(27205) == 1


def test_importar_a_exportacao_na_mesma_base_nao_duplica_nada(sessao, tmp_path):
    seed_com_uma_playlist_nova(sessao)
    ficheiro = tmp_path / "exportacao.json"
    exportar_para_ficheiro(sessao, ficheiro)

    relatorio = importar_seed(sessao, ficheiro)

    assert relatorio.utilizadores_criados == relatorio.playlists_criadas == relatorio.notas_criadas == 0
    assert relatorio.playlists_existentes == 11  # as 10 do seed + a criada na app


def test_levar_a_exportacao_para_outra_base_de_dados_reproduz_os_dados(sessao, tmp_path):
    seed_com_uma_playlist_nova(sessao)
    ficheiro = tmp_path / "exportacao.json"
    original = exportar_para_ficheiro(sessao, ficheiro)

    outra_engine = criar_engine("sqlite://")  # uma instalação nova, vazia
    criar_tabelas(outra_engine)
    with Session(outra_engine) as outra_sessao:
        importar_seed(outra_sessao, ficheiro)
        copia = exportar_dados(outra_sessao)
    outra_engine.dispose()

    assert copia.model_dump(exclude={"descricao"}) == original.model_dump(exclude={"descricao"})
