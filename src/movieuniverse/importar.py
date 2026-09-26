"""Importação dos dados de exemplo (dados/seed_playlists.json).

Comando:  python -m movieuniverse importar-seed

Regras (ver DECISIONS.md, secção "Problemas encontrados nos dados"):
  - Playlists marcadas como apagadas são importadas COM apagada=True (não aparecem na app).
  - Um filme repetido na mesma playlist fica só na 1.ª ocorrência (menor "ordem").
  - Pode correr várias vezes: só cria o que falta e NUNCA altera nem apaga o que já existe.
      utilizadores -> reconhecidos pelo nome (sem distinguir maiúsculas)
      playlists    -> reconhecidas pelo id do seed ("pl-01"), guardado em Playlist.id_seed
      notas        -> reconhecidas pelo par (utilizador, filme)
  - Não contacta a TMDB: guarda só os tmdb_id. Os dados dos filmes chegam quando forem vistos.
  - Tudo numa transação: se algo falhar a meio, nada fica gravado.
"""
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from movieuniverse.config import RAIZ_PROJETO
from movieuniverse.entidades import Nota, Playlist, PlaylistFilme, Utilizador

FICHEIRO_SEED = RAIZ_PROJETO / "dados" / "seed_playlists.json"


# --- Formato do ficheiro -------------------------------------------------------------
# Validar o JSON com Pydantic apanha logo um ficheiro mal formado, com uma mensagem clara
# (≈ desserializar para DTOs com [Required] antes de tocar na base de dados).

class SeedUtilizador(BaseModel):
    nome: str = Field(min_length=1)


class SeedFilme(BaseModel):
    tmdb_id: int = Field(gt=0)
    ordem: int


class SeedPlaylist(BaseModel):
    id: str
    nome: str
    utilizador: str
    apagada: bool = False
    filmes: list[SeedFilme] = []


class SeedNota(BaseModel):
    utilizador: str
    tmdb_id: int = Field(gt=0)
    estrelas: int = Field(ge=1, le=10)
    data: date


class SeedFicheiro(BaseModel):
    """O ficheiro inteiro. A exportação (exportar.py) usa este mesmo modelo."""

    versao: str
    descricao: str = ""
    utilizadores: list[SeedUtilizador]
    playlists: list[SeedPlaylist]
    notas: list[SeedNota]


# --- Relatório -----------------------------------------------------------------------

@dataclass
class Relatorio:
    """O que a importação fez (≈ um record C# com contadores)."""

    utilizadores_criados: int = 0
    utilizadores_existentes: int = 0
    playlists_criadas: int = 0
    playlists_apagadas: int = 0  # das criadas, quantas vinham marcadas como apagadas
    playlists_existentes: int = 0
    notas_criadas: int = 0
    notas_existentes: int = 0
    avisos: list[str] = field(default_factory=list)

    def texto(self) -> str:
        linhas = [
            f"  Utilizadores: {self.utilizadores_criados} criados, {self.utilizadores_existentes} já existiam",
            f"  Playlists:    {self.playlists_criadas} criadas ({self.playlists_apagadas} marcadas como apagadas), "
            f"{self.playlists_existentes} já existiam",
            f"  Notas:        {self.notas_criadas} criadas, {self.notas_existentes} já existiam",
        ]
        if self.avisos:
            linhas.append("  Avisos:")
            linhas += [f"   - {aviso}" for aviso in self.avisos]
        return "\n".join(linhas)


# --- Importação ----------------------------------------------------------------------

def importar_seed(sessao: Session, caminho: Path = FICHEIRO_SEED) -> Relatorio:
    seed = SeedFicheiro.model_validate_json(Path(caminho).read_text(encoding="utf-8"))
    relatorio = Relatorio()

    utilizadores = _importar_utilizadores(sessao, seed, relatorio)
    _importar_playlists(sessao, seed, utilizadores, relatorio)
    _importar_notas(sessao, seed, utilizadores, relatorio)
    _avisar_filmes_so_em_apagadas(seed, relatorio)

    sessao.commit()  # só aqui fica tudo gravado (tudo ou nada)
    return relatorio


def _importar_utilizadores(sessao: Session, seed: SeedFicheiro, relatorio: Relatorio) -> dict[str, Utilizador]:
    """Devolve um dicionário nome (em minúsculas) -> Utilizador, para os passos seguintes."""
    utilizadores: dict[str, Utilizador] = {}
    for item in seed.utilizadores:
        nome = item.nome.strip()
        if nome.lower() in utilizadores:
            continue  # o mesmo nome duas vezes no ficheiro
        utilizador = sessao.scalar(select(Utilizador).where(Utilizador.nome == nome))
        if utilizador:
            relatorio.utilizadores_existentes += 1
        else:
            utilizador = Utilizador(nome=nome)
            sessao.add(utilizador)
            relatorio.utilizadores_criados += 1
        utilizadores[nome.lower()] = utilizador
    sessao.flush()  # envia os INSERT para os utilizadores novos receberem id
    return utilizadores


def _importar_playlists(
    sessao: Session, seed: SeedFicheiro, utilizadores: dict[str, Utilizador], relatorio: Relatorio
) -> None:
    for item in seed.playlists:
        dono = utilizadores.get(item.utilizador.strip().lower())
        if dono is None:
            relatorio.avisos.append(f"{item.id}: o utilizador '{item.utilizador}' não existe; playlist ignorada.")
            continue
        if sessao.scalar(select(Playlist).where(Playlist.id_seed == item.id)):
            relatorio.playlists_existentes += 1  # já importada antes: não se toca
            continue

        playlist = Playlist(nome=item.nome, utilizador=dono, apagada=item.apagada, id_seed=item.id)
        vistos: set[int] = set()
        for filme in sorted(item.filmes, key=lambda f: f.ordem):  # pela ordem: a 1.ª ocorrência ganha
            if filme.tmdb_id in vistos:
                relatorio.avisos.append(
                    f"{item.id}: o filme {filme.tmdb_id} aparece repetido (ordem {filme.ordem}); "
                    "ficou só a 1.ª ocorrência."
                )
                continue
            vistos.add(filme.tmdb_id)
            playlist.filmes.append(PlaylistFilme(tmdb_id=filme.tmdb_id, ordem=filme.ordem))

        sessao.add(playlist)
        relatorio.playlists_criadas += 1
        if item.apagada:
            relatorio.playlists_apagadas += 1


def _importar_notas(
    sessao: Session, seed: SeedFicheiro, utilizadores: dict[str, Utilizador], relatorio: Relatorio
) -> None:
    sessao.flush()
    vistas: set[tuple[int, int]] = set()  # (utilizador_id, tmdb_id) já tratados nesta importação
    for item in seed.notas:
        autor = utilizadores.get(item.utilizador.strip().lower())
        if autor is None:
            relatorio.avisos.append(f"Nota de '{item.utilizador}' ao filme {item.tmdb_id}: utilizador inexistente; ignorada.")
            continue
        chave = (autor.id, item.tmdb_id)
        existe = sessao.scalar(select(Nota).where(Nota.utilizador_id == autor.id, Nota.tmdb_id == item.tmdb_id))
        if existe or chave in vistas:
            relatorio.notas_existentes += 1  # nunca sobrescreve uma nota que já existe
            continue
        vistas.add(chave)
        sessao.add(Nota(utilizador=autor, tmdb_id=item.tmdb_id, estrelas=item.estrelas, data=item.data))
        relatorio.notas_criadas += 1


def _avisar_filmes_so_em_apagadas(seed: SeedFicheiro, relatorio: Relatorio) -> None:
    em_ativas = {f.tmdb_id for p in seed.playlists if not p.apagada for f in p.filmes}
    em_apagadas = {f.tmdb_id for p in seed.playlists if p.apagada for f in p.filmes}
    so_em_apagadas = sorted(em_apagadas - em_ativas)
    if so_em_apagadas:
        relatorio.avisos.append(
            "Filmes que só existem em playlists apagadas (ficam guardados, mas não aparecem na aplicação): "
            + ", ".join(map(str, so_em_apagadas))
            + "."
        )
