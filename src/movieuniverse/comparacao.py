"""Comparação de duas playlists (Passo 8).

Função PURA, como a nota combinada: recebe os filmes de cada playlist já com a nota
combinada calculada e devolve o resultado. Não depende da base de dados nem da rede.

Regras (ver DECISIONS.md, secção "Comparação de playlists"):
  - O "rating" de uma playlist é a MÉDIA das notas combinadas dos seus filmes.
  - Filmes sem nota combinada (sem votos nenhuns, ou indisponíveis) ficam de fora da média,
    mas são contados e indicados no resultado.
  - Ganha a playlist com a média mais alta. Médias iguais até à 2.ª casa decimal = empate.
  - Se uma das playlists não tiver nenhum filme com nota, não há vencedora.
Extras: número de filmes, melhor filme de cada uma, filmes em comum e filmes só numa delas.
"""
from typing import Literal

from pydantic import BaseModel

from movieuniverse.nota_combinada import NotaCombinada


def _pt(valor: float, casas: int = 2) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


class FilmeAvaliado(BaseModel):
    """Um filme de uma playlist com a sua nota combinada (entrada e saída da comparação)."""

    tmdb_id: int
    titulo: str
    ano: int | None = None
    poster_url: str | None = None
    nota_combinada: NotaCombinada


class LadoComparacao(BaseModel):
    """O resumo de uma das duas playlists."""

    playlist_id: int
    nome: str
    dono: str
    num_filmes: int
    num_filmes_com_nota: int
    media: float | None  # média das notas combinadas; None se nenhum filme tiver nota
    melhor_filme: FilmeAvaliado | None
    so_nesta: list[FilmeAvaliado]  # filmes que a outra playlist não tem


class ComparacaoPlaylists(BaseModel):
    a: LadoComparacao
    b: LadoComparacao
    vencedora: Literal["a", "b", "empate"] | None  # None = não há informação para comparar
    diferenca: float | None
    em_comum: list[FilmeAvaliado]
    explicacao: str


def _resumir(
    playlist_id: int, nome: str, dono: str, filmes: list[FilmeAvaliado], ids_da_outra: set[int]
) -> LadoComparacao:
    com_nota = [f for f in filmes if f.nota_combinada.valor is not None]
    media = round(sum(f.nota_combinada.valor for f in com_nota) / len(com_nota), 2) if com_nota else None
    melhor = max(com_nota, key=lambda f: f.nota_combinada.valor, default=None)
    return LadoComparacao(
        playlist_id=playlist_id,
        nome=nome,
        dono=dono,
        num_filmes=len(filmes),
        num_filmes_com_nota=len(com_nota),
        media=media,
        melhor_filme=melhor,
        so_nesta=[f for f in filmes if f.tmdb_id not in ids_da_outra],
    )


def comparar_playlists(
    a: tuple[int, str, str, list[FilmeAvaliado]],
    b: tuple[int, str, str, list[FilmeAvaliado]],
) -> ComparacaoPlaylists:
    """Compara duas playlists. Cada uma é (id, nome, dono, filmes com nota combinada)."""
    ids_a = {f.tmdb_id for f in a[3]}
    ids_b = {f.tmdb_id for f in b[3]}
    lado_a = _resumir(*a, ids_da_outra=ids_b)
    lado_b = _resumir(*b, ids_da_outra=ids_a)
    em_comum = [f for f in a[3] if f.tmdb_id in ids_b]  # pela ordem da playlist A

    if lado_a.media is None or lado_b.media is None:
        sem_nota = lado_a.nome if lado_a.media is None else lado_b.nome
        return ComparacaoPlaylists(
            a=lado_a, b=lado_b, vencedora=None, diferenca=None, em_comum=em_comum,
            explicacao=f"Informação insuficiente: a playlist \"{sem_nota}\" não tem nenhum filme "
                       "com nota combinada, por isso não é possível compará-las.",
        )

    diferenca = round(abs(lado_a.media - lado_b.media), 2)
    if diferenca == 0:
        vencedora, explicacao = "empate", (
            f"Empate: as duas playlists têm a mesma média de nota combinada ({_pt(lado_a.media)})."
        )
    else:
        vencedora = "a" if lado_a.media > lado_b.media else "b"
        melhor, pior = (lado_a, lado_b) if vencedora == "a" else (lado_b, lado_a)
        explicacao = (
            f"\"{melhor.nome}\" tem o melhor rating: média de nota combinada {_pt(melhor.media)} "
            f"contra {_pt(pior.media)} ({_pt(diferenca)} pontos de diferença)."
        )

    sem_nota = (lado_a.num_filmes - lado_a.num_filmes_com_nota) + (lado_b.num_filmes - lado_b.num_filmes_com_nota)
    if sem_nota:
        explicacao += f" {sem_nota} filme(s) sem nota combinada ficaram de fora das médias."

    return ComparacaoPlaylists(
        a=lado_a, b=lado_b, vencedora=vencedora, diferenca=diferenca, em_comum=em_comum,
        explicacao=explicacao,
    )
