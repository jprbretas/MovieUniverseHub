"""Servidor MCP do MovieUniverse Hub (extra, além do enunciado).

Deixa um cliente MCP, como o Claude Desktop, pesquisar filmes, ver a nota combinada e
comparar playlists. Arranca com `python -m movieuniverse mcp`, lançado pelo próprio cliente.

  - Só consulta: nenhuma ferramenta altera utilizadores, playlists ou notas (só a cache da TMDB).
  - Usa as mesmas regras da API (servicos.py e catalogo.py) e não precisa do site a correr.
  - Transporte stdio: o stdout pertence ao protocolo, por isso este código nunca usa print().

O nome, a docstring e os tipos de cada ferramenta são o que a IA lê para decidir como a usar.
Decisões em DECISIONS.md, secção "Servidor MCP".
"""
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from movieuniverse import servicos
from movieuniverse.catalogo import Catalogo
from movieuniverse.comparacao import FilmeAvaliado, LadoComparacao
from movieuniverse.db import SessaoLocal
from movieuniverse.dependencias import obter_cliente_tmdb
from movieuniverse.entidades import Utilizador
from movieuniverse.nota_combinada import NotaCombinada
from movieuniverse.tmdb import PAGINA_MAXIMA, ClienteTMDB, ErroTMDB

# O que a IA lê ao ligar-se: para que serve o servidor e como usar as ferramentas juntas.
INSTRUCOES = """\
MovieUniverse Hub: catálogo de filmes (dados da TMDB), playlists e notas dos utilizadores.
- Os filmes identificam-se pelo tmdb_id: use pesquisar_filmes para o descobrir.
- As playlists identificam-se pelo id: use listar_playlists para o descobrir.
- A "nota combinada" junta a nota da TMDB às notas dos utilizadores, pesando o número de
  votos (média bayesiana com 100 votos imaginários de nota 6,5). Sem votos nenhuns, não há
  nota ("informação insuficiente"). Cada resposta traz a explicação do cálculo.
- As ferramentas só consultam: não é possível criar ou alterar playlists nem notas por aqui.
"""

# Diz ao cliente que a ferramenta não altera nada.
SO_LEITURA = ToolAnnotations(read_only_hint=True)


# --- Formato das respostas: pequeno, porque cada campo ocupa espaço na conversa da IA ---

class FilmeEncontrado(BaseModel):
    tmdb_id: int
    titulo: str
    ano: int | None
    nota_tmdb: str = Field(description='Ex.: "8,4 · 40 258 votos" ou "sem votos"')


class ResultadoPesquisa(BaseModel):
    total_resultados: int
    pagina: int
    total_paginas: int
    filmes: list[FilmeEncontrado]


class NotaDeUtilizador(BaseModel):
    utilizador: str
    estrelas: int


class FichaFilme(BaseModel):
    tmdb_id: int
    titulo: str
    titulo_original: str
    ano: int | None
    generos: list[str]
    duracao_min: int | None
    sinopse: str
    nota_tmdb: str
    nota_combinada: NotaCombinada
    notas_dos_utilizadores: list[NotaDeUtilizador]


class PlaylistResumida(BaseModel):
    id: int
    nome: str
    dono: str
    num_filmes: int


class FilmeDaPlaylist(BaseModel):
    tmdb_id: int
    titulo: str
    ano: int | None
    nota_combinada: str = Field(description='Ex.: "8,4 · 30 003 votos" ou "informação insuficiente"')


class PlaylistComFilmes(BaseModel):
    id: int
    nome: str
    dono: str
    filmes: list[FilmeDaPlaylist]


class LadoResumido(BaseModel):
    playlist_id: int
    nome: str
    dono: str
    num_filmes: int
    num_filmes_com_nota: int
    media_nota_combinada: float | None
    melhor_filme: str | None
    so_nesta: list[str]


class ResumoComparacao(BaseModel):
    vencedora: str | None = Field(description='Nome da playlist com melhor rating, "empate" ou null')
    explicacao: str
    a: LadoResumido
    b: LadoResumido
    em_comum: list[str]


def _descrever(filme: FilmeAvaliado) -> str:
    """"Interstellar (2014) · 8,4 · 38 002 votos": o título com o ano e a nota combinada."""
    ano = f" ({filme.ano})" if filme.ano else ""
    return f"{filme.titulo}{ano} · {filme.nota_combinada.texto}"


def _resumir_lado(lado: LadoComparacao) -> LadoResumido:
    return LadoResumido(
        playlist_id=lado.playlist_id,
        nome=lado.nome,
        dono=lado.dono,
        num_filmes=lado.num_filmes,
        num_filmes_com_nota=lado.num_filmes_com_nota,
        media_nota_combinada=lado.media,
        melhor_filme=_descrever(lado.melhor_filme) if lado.melhor_filme else None,
        so_nesta=[_descrever(f) for f in lado.so_nesta],
    )


# --- O servidor ----------------------------------------------------------------------

def criar_servidor(
    fabrica_sessao: Callable[[], Session] = SessaoLocal,
    obter_tmdb: Callable[[], ClienteTMDB] = obter_cliente_tmdb,
) -> MCPServer:
    """Monta o servidor MCP com as suas ferramentas.

    Os parâmetros permitem aos testes usar uma base de dados em memória e uma TMDB falsa.
    """
    mcp = MCPServer("MovieUniverse Hub", instructions=INSTRUCOES, version="1.0.0")

    @contextmanager
    def trabalho() -> Iterator[Session]:
        """Uma sessão por chamada de ferramenta.

        Traduz os erros da aplicação em `ToolError`, cuja mensagem chega à IA para ela poder
        corrigir o pedido.
        """
        with fabrica_sessao() as sessao:
            try:
                yield sessao
            except (servicos.NaoEncontrado, ErroTMDB) as erro:
                raise ToolError(str(erro)) from erro

    def catalogo(sessao: Session) -> Catalogo:
        # Criado só quando é preciso: sem token, as ferramentas de playlists continuam a funcionar.
        return Catalogo(sessao, obter_tmdb())

    @mcp.tool(annotations=SO_LEITURA)
    def pesquisar_filmes(
        titulo: Annotated[str, Field(min_length=1, max_length=200, description="Título ou parte do título")],
        pagina: Annotated[int, Field(ge=1, le=PAGINA_MAXIMA, description="Página de resultados")] = 1,
    ) -> ResultadoPesquisa:
        """Pesquisa filmes por título na TMDB (20 por página). Devolve o tmdb_id de cada filme,
        que as outras ferramentas usam, o ano e a nota da TMDB com o número de votos."""
        with trabalho() as sessao:
            pagina_tmdb = catalogo(sessao).pesquisar(titulo, pagina)
        return ResultadoPesquisa(
            total_resultados=pagina_tmdb.total_resultados,
            pagina=pagina_tmdb.pagina,
            total_paginas=min(pagina_tmdb.total_paginas, PAGINA_MAXIMA),
            filmes=[
                FilmeEncontrado(tmdb_id=f.tmdb_id, titulo=f.titulo, ano=f.ano, nota_tmdb=f.nota_tmdb_texto)
                for f in pagina_tmdb.filmes
            ],
        )

    @mcp.tool(annotations=SO_LEITURA)
    def ficha_filme(
        tmdb_id: Annotated[int, Field(gt=0, description="Id do filme na TMDB (ex.: 603)")],
    ) -> FichaFilme:
        """Ficha de um filme: sinopse, géneros, duração, nota da TMDB, a nota combinada (com a
        explicação do cálculo) e as notas que os utilizadores da aplicação lhe deram."""
        with trabalho() as sessao:
            filme = catalogo(sessao).detalhe(tmdb_id)
            notas = servicos.notas_do_filme(sessao, tmdb_id)
            return FichaFilme(
                tmdb_id=filme.tmdb_id,
                titulo=filme.titulo,
                titulo_original=filme.titulo_original,
                ano=filme.ano,
                generos=[g.nome for g in filme.generos],
                duracao_min=filme.duracao_min,
                sinopse=filme.sinopse,
                nota_tmdb=filme.nota_tmdb_texto,
                nota_combinada=servicos.nota_combinada_do_filme(sessao, filme),
                notas_dos_utilizadores=[NotaDeUtilizador(utilizador=n.utilizador.nome, estrelas=n.estrelas) for n in notas],
            )

    @mcp.tool(annotations=SO_LEITURA)
    def listar_utilizadores() -> list[str]:
        """Os nomes dos utilizadores da aplicação, por ordem alfabética."""
        with trabalho() as sessao:
            return [u.nome for u in servicos.listar_utilizadores(sessao)]

    @mcp.tool(annotations=SO_LEITURA)
    def listar_playlists(
        utilizador: Annotated[str | None, Field(description="Nome do dono; se ficar vazio, lista as de todos")] = None,
    ) -> list[PlaylistResumida]:
        """As playlists (sem as apagadas), com o id que ver_playlist e comparar_playlists usam."""
        with trabalho() as sessao:
            playlists = servicos.listar_playlists(sessao)
            if utilizador:
                # A coluna do nome não distingue maiúsculas: "Ana" encontra a "ana".
                dono = sessao.scalar(select(Utilizador).where(Utilizador.nome == utilizador.strip()))
                if dono is None:
                    nomes = ", ".join(u.nome for u in servicos.listar_utilizadores(sessao))
                    raise ToolError(f"Não existe nenhum utilizador chamado '{utilizador}'. Utilizadores: {nomes}.")
                playlists = [p for p in playlists if p.utilizador_id == dono.id]
            return [
                PlaylistResumida(id=p.id, nome=p.nome, dono=p.utilizador.nome, num_filmes=len(p.filmes))
                for p in playlists
            ]

    @mcp.tool(annotations=SO_LEITURA)
    def ver_playlist(
        playlist_id: Annotated[int, Field(gt=0, description="Id da playlist (ver listar_playlists)")],
    ) -> PlaylistComFilmes:
        """Os filmes de uma playlist, pela ordem, cada um com a sua nota combinada."""
        with trabalho() as sessao:
            playlist = servicos.obter_playlist(sessao, playlist_id)
            filmes = servicos.filmes_avaliados(sessao, catalogo(sessao), playlist)
            return PlaylistComFilmes(
                id=playlist.id,
                nome=playlist.nome,
                dono=playlist.utilizador.nome,
                filmes=[
                    FilmeDaPlaylist(tmdb_id=f.tmdb_id, titulo=f.titulo, ano=f.ano, nota_combinada=f.nota_combinada.texto)
                    for f in filmes
                ],
            )

    @mcp.tool(annotations=SO_LEITURA)
    def comparar_playlists(
        playlist_a: Annotated[int, Field(gt=0, description="Id da 1.ª playlist")],
        playlist_b: Annotated[int, Field(gt=0, description="Id da 2.ª playlist")],
    ) -> ResumoComparacao:
        """Compara duas playlists: qual tem o melhor rating (a média das notas combinadas dos
        seus filmes), o número de filmes, o melhor filme de cada uma, os filmes em comum e os
        que só estão numa delas. Usa as mesmas regras do ecrã Comparar do site."""
        if playlist_a == playlist_b:
            raise ToolError("Escolhe duas playlists diferentes para comparar.")
        with trabalho() as sessao:
            comparacao = servicos.comparar(sessao, catalogo(sessao), playlist_a, playlist_b)
        nomes = {"a": comparacao.a.nome, "b": comparacao.b.nome, "empate": "empate"}
        return ResumoComparacao(
            vencedora=nomes.get(comparacao.vencedora) if comparacao.vencedora else None,
            explicacao=comparacao.explicacao,
            a=_resumir_lado(comparacao.a),
            b=_resumir_lado(comparacao.b),
            em_comum=[_descrever(f) for f in comparacao.em_comum],
        )

    return mcp
