"""Regras de negócio de utilizadores, playlists e notas (camada de negócio).

Equivalente C#: uma classe de serviço (ex.: PlaylistService) que recebe o DbContext.
Aqui são funções simples que recebem a `sessao` como primeiro parâmetro.

As rotas (rotas/*.py) só tratam de HTTP; tudo o que é regra ("uma nota por utilizador e
por filme", "apagar só marca como apagada", "adicionar duas vezes não duplica") está aqui.
Isto também torna as regras fáceis de reutilizar, por exemplo na importação do seed.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from movieuniverse.entidades import Nota, Playlist, PlaylistFilme, Utilizador, agora
from movieuniverse.nota_combinada import NotaCombinada, calcular_nota_combinada
from movieuniverse.tmdb import FilmeResumo


class NaoEncontrado(Exception):
    """O utilizador ou a playlist não existe (a API responde 404)."""


# --- Utilizadores ----------------------------------------------------------------

def listar_utilizadores(sessao: Session) -> list[Utilizador]:
    return list(sessao.scalars(select(Utilizador).order_by(Utilizador.nome)))


def entrar(sessao: Session, nome: str) -> Utilizador:
    """Devolve o utilizador com este nome e cria-o se ainda não existir.

    Não há palavra-passe (ver DECISIONS.md): "entrar" é só dizer quem somos.
    A procura não distingue maiúsculas, graças ao collation NOCASE da coluna.
    """
    nome = nome.strip()
    utilizador = sessao.scalar(select(Utilizador).where(Utilizador.nome == nome))
    if utilizador is None:
        utilizador = Utilizador(nome=nome)
        sessao.add(utilizador)
        sessao.commit()
    return utilizador


def obter_utilizador(sessao: Session, utilizador_id: int) -> Utilizador:
    utilizador = sessao.get(Utilizador, utilizador_id)
    if utilizador is None:
        raise NaoEncontrado(f"Não existe nenhum utilizador com id {utilizador_id}.")
    return utilizador


# --- Playlists -------------------------------------------------------------------

def playlists_do_utilizador(sessao: Session, utilizador_id: int) -> list[Playlist]:
    obter_utilizador(sessao, utilizador_id)  # 404 se o utilizador não existir
    consulta = (
        select(Playlist)
        .where(Playlist.utilizador_id == utilizador_id, Playlist.apagada.is_(False))
        .order_by(Playlist.criada_em, Playlist.id)
    )
    return list(sessao.scalars(consulta))


def criar_playlist(sessao: Session, utilizador_id: int, nome: str) -> Playlist:
    utilizador = obter_utilizador(sessao, utilizador_id)
    playlist = Playlist(nome=nome.strip(), utilizador=utilizador)
    sessao.add(playlist)
    sessao.commit()
    return playlist


def obter_playlist(sessao: Session, playlist_id: int) -> Playlist:
    """Devolve a playlist; as apagadas contam como inexistentes."""
    playlist = sessao.get(Playlist, playlist_id)
    if playlist is None or playlist.apagada:
        raise NaoEncontrado(f"Não existe nenhuma playlist com id {playlist_id}.")
    return playlist


def apagar_playlist(sessao: Session, playlist_id: int) -> None:
    """Soft delete: a playlist fica na base de dados, mas marcada como apagada."""
    obter_playlist(sessao, playlist_id).apagada = True
    sessao.commit()


def adicionar_filme(sessao: Session, playlist_id: int, tmdb_id: int) -> Playlist:
    """Adiciona o filme no fim da playlist. Se já lá estiver, não faz nada (idempotente)."""
    playlist = obter_playlist(sessao, playlist_id)
    if tmdb_id not in [f.tmdb_id for f in playlist.filmes]:
        ultima_ordem = sessao.scalar(
            select(func.max(PlaylistFilme.ordem)).where(PlaylistFilme.playlist_id == playlist_id)
        )
        playlist.filmes.append(PlaylistFilme(tmdb_id=tmdb_id, ordem=(ultima_ordem or 0) + 1))
        sessao.commit()
    return playlist


def remover_filme(sessao: Session, playlist_id: int, tmdb_id: int) -> Playlist:
    """Tira o filme da playlist. Se não estiver lá, não faz nada (idempotente)."""
    playlist = obter_playlist(sessao, playlist_id)
    playlist.filmes = [f for f in playlist.filmes if f.tmdb_id != tmdb_id]  # delete-orphan apaga a linha
    sessao.commit()
    return playlist


# --- Notas -----------------------------------------------------------------------

def dar_nota(sessao: Session, utilizador_id: int, tmdb_id: int, estrelas: int) -> Nota:
    """Cria a nota do utilizador para o filme ou altera a que já existia (upsert)."""
    utilizador = obter_utilizador(sessao, utilizador_id)
    nota = sessao.scalar(
        select(Nota).where(Nota.utilizador_id == utilizador_id, Nota.tmdb_id == tmdb_id)
    )
    if nota is None:
        nota = Nota(utilizador=utilizador, tmdb_id=tmdb_id)
        sessao.add(nota)
    nota.estrelas = estrelas
    nota.data = agora().date()
    sessao.commit()
    return nota


def remover_nota(sessao: Session, utilizador_id: int, tmdb_id: int) -> None:
    obter_utilizador(sessao, utilizador_id)
    nota = sessao.scalar(
        select(Nota).where(Nota.utilizador_id == utilizador_id, Nota.tmdb_id == tmdb_id)
    )
    if nota is not None:
        sessao.delete(nota)
        sessao.commit()


def notas_do_filme(sessao: Session, tmdb_id: int) -> list[Nota]:
    return list(sessao.scalars(select(Nota).where(Nota.tmdb_id == tmdb_id).order_by(Nota.data.desc())))


def nota_combinada_do_filme(sessao: Session, filme: FilmeResumo) -> NotaCombinada:
    """Junta a nota da TMDB (que vem no filme) às notas dos utilizadores guardadas na base.

    O cálculo em si é feito pela função pura calcular_nota_combinada(); aqui só se vão
    buscar os números.
    """
    notas = notas_do_filme(sessao, filme.tmdb_id)
    media_app = sum(n.estrelas for n in notas) / len(notas) if notas else None
    return calcular_nota_combinada(filme.media_votos, filme.num_votos, media_app, len(notas))
