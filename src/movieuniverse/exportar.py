"""Exportação dos dados da aplicação para JSON, no mesmo formato do seed.

Comando:  python -m movieuniverse exportar [--ficheiro dados/exportacao.json]

É o inverso da importação (importar.py) e usa os MESMOS modelos Pydantic, por isso o
ficheiro gerado pode ser importado noutra instalação com
"python -m movieuniverse importar-seed --ficheiro <ficheiro>".

  - Exporta tudo: utilizadores, playlists (as apagadas também, marcadas como tal) e notas.
  - As playlists do seed mantêm o seu id ("pl-01"). As criadas na aplicação não têm id
    externo; na primeira exportação recebem um ("app-" + 8 caracteres aleatórios), guardado
    na coluna id_seed. Assim, importar o ficheiro de volta reconhece-as e não as duplica.
  - Não contacta a TMDB: os filmes são exportados só pelo tmdb_id, como no seed.
"""
import secrets
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from movieuniverse.config import RAIZ_PROJETO
from movieuniverse.entidades import Nota, Playlist, Utilizador
from movieuniverse.importar import SeedFicheiro, SeedFilme, SeedNota, SeedPlaylist, SeedUtilizador

FICHEIRO_EXPORTACAO = RAIZ_PROJETO / "dados" / "exportacao.json"


def exportar_dados(sessao: Session) -> SeedFicheiro:
    """Lê a base de dados e devolve o conteúdo no formato do seed (sem escrever ficheiros)."""
    utilizadores = sessao.scalars(select(Utilizador).order_by(Utilizador.id)).all()
    playlists = sessao.scalars(select(Playlist).order_by(Playlist.id)).all()
    notas = sessao.scalars(select(Nota).order_by(Nota.id)).all()

    for playlist in playlists:
        if playlist.id_seed is None:  # criada na aplicação: ganha um id externo estável
            playlist.id_seed = f"app-{secrets.token_hex(4)}"

    dados = SeedFicheiro(
        versao="1.0",
        descricao=f"Exportado do MovieUniverse Hub em {date.today().isoformat()}",
        utilizadores=[SeedUtilizador(nome=u.nome) for u in utilizadores],
        playlists=[
            SeedPlaylist(
                id=p.id_seed,
                nome=p.nome,
                utilizador=p.utilizador.nome,
                apagada=p.apagada,
                filmes=[SeedFilme(tmdb_id=f.tmdb_id, ordem=f.ordem) for f in p.filmes],
            )
            for p in playlists
        ],
        notas=[
            SeedNota(utilizador=n.utilizador.nome, tmdb_id=n.tmdb_id, estrelas=n.estrelas, data=n.data)
            for n in notas
        ],
    )
    sessao.commit()  # grava os ids externos que tenham sido criados agora
    return dados


def exportar_para_ficheiro(sessao: Session, caminho: Path = FICHEIRO_EXPORTACAO) -> SeedFicheiro:
    """Exporta e escreve o JSON (UTF-8, indentado, para ser legível)."""
    dados = exportar_dados(sessao)
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(dados.model_dump_json(indent=2), encoding="utf-8")
    return dados
