"""Integração com a API da TMDB.

Este módulo tem duas partes:
  1. Modelos (os "DTOs") que representam as respostas da TMDB.
  2. O ClienteTMDB, que faz os pedidos HTTP e devolve esses modelos.

Os campos da TMDB estão em inglês (title, vote_count...). Nos nossos modelos usamos
nomes em português e ligamo-los ao JSON da TMDB com `validation_alias` (≈ [JsonPropertyName]
em C#, mas só para LER). Ao escrever (ex.: nas respostas da nossa API e no Swagger) usam-se
os nomes em português. Assim o resto da aplicação nunca vê os nomes da TMDB.

Só declaramos os campos de que precisamos: o Pydantic ignora os restantes
(ex.: o campo não documentado "softcore" que apareceu nas respostas reais).
"""
from datetime import date
from typing import Self

import httpx2
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from movieuniverse.config import Settings, get_settings

URL_BASE = "https://api.themoviedb.org/3"
URL_IMAGENS = "https://image.tmdb.org/t/p/w500"  # base + tamanho (500 px de largura)
LINGUA_PADRAO = "pt-PT"
LINGUA_ALTERNATIVA = "en-US"  # usada quando a sinopse em pt-PT vem vazia
PAGINA_MAXIMA = 500           # a TMDB não devolve páginas acima da 500


def formatar_nota_tmdb(media: float, votos: int) -> str:
    """Texto da nota como o enunciado pede: "7,8 · 12 340 votos" ou "sem votos" (nunca "0")."""
    if votos <= 0:
        return "sem votos"
    media_pt = f"{media:.1f}".replace(".", ",")      # 8.374 -> "8,4"
    votos_pt = f"{votos:,}".replace(",", " ")        # 12340 -> "12 340"
    palavra = "voto" if votos == 1 else "votos"
    return f"{media_pt} · {votos_pt} {palavra}"


class ModeloTMDB(BaseModel):
    """Configuração comum a todos os modelos (≈ uma classe base com os atributos de JSON)."""

    model_config = ConfigDict(
        validate_by_alias=True,  # lê o JSON da TMDB pelos nomes em inglês (validation_alias)...
        validate_by_name=True,   # ...e também aceita os nomes em português (útil nos testes)
        extra="ignore",          # campos que não declarámos são descartados
    )


class Genero(ModeloTMDB):
    id: int
    nome: str = Field(validation_alias="name")


class FilmeResumo(ModeloTMDB):
    """Um filme como aparece nos resultados de pesquisa (/search/movie)."""

    tmdb_id: int = Field(validation_alias="id")
    titulo: str = Field(validation_alias="title")
    titulo_original: str = Field(default="", validation_alias="original_title")
    data_estreia: date | None = Field(default=None, validation_alias="release_date")
    poster_path: str | None = Field(default=None, validation_alias="poster_path")
    media_votos: float = Field(default=0.0, validation_alias="vote_average")
    num_votos: int = Field(default=0, validation_alias="vote_count")

    @field_validator("data_estreia", mode="before")
    @classmethod
    def data_vazia_e_none(cls, valor):
        """A TMDB manda "" quando não sabe a data; "" não é uma data válida, por isso vira None."""
        return valor or None

    # @computed_field + @property ≈ propriedade só de leitura em C# (get => ...).
    # O computed_field faz com que apareça também no JSON que a nossa API devolver.
    @computed_field
    @property
    def ano(self) -> int | None:
        return self.data_estreia.year if self.data_estreia else None

    @computed_field
    @property
    def poster_url(self) -> str | None:
        return f"{URL_IMAGENS}{self.poster_path}" if self.poster_path else None

    @computed_field
    @property
    def nota_tmdb_texto(self) -> str:
        return formatar_nota_tmdb(self.media_votos, self.num_votos)


class FilmeDetalhe(FilmeResumo):
    """Um filme com todos os dados da ficha (/movie/{id}). Herda tudo do FilmeResumo."""

    sinopse: str = Field(default="", validation_alias="overview")
    generos: list[Genero] = Field(default_factory=list, validation_alias="genres")
    duracao_min: int | None = Field(default=None, validation_alias="runtime")

    @field_validator("sinopse", mode="before")
    @classmethod
    def sinopse_none_e_vazia(cls, valor):
        return valor or ""

    @field_validator("duracao_min", mode="before")
    @classmethod
    def duracao_zero_e_desconhecida(cls, valor):
        """A TMDB usa 0 quando não sabe a duração; guardamos None ("desconhecida")."""
        return valor or None


class PaginaPesquisa(ModeloTMDB):
    """Uma página de resultados de /search/movie (a TMDB devolve 20 por página)."""

    pagina: int = Field(validation_alias="page")
    total_paginas: int = Field(validation_alias="total_pages")
    total_resultados: int = Field(validation_alias="total_results")
    filmes: list[FilmeResumo] = Field(validation_alias="results")


# ---------------------------------------------------------------------------
# Erros: cada problema tem a sua exceção, para a camada da API (api.py) poder
# responder com o código HTTP certo (ex.: FilmeNaoEncontrado -> 404).
# ≈ classes que herdam de Exception em C#.
# ---------------------------------------------------------------------------
class ErroTMDB(Exception):
    """Erro genérico ao falar com a TMDB (base das outras)."""


class TokenInvalido(ErroTMDB):
    """401: token em falta ou recusado pela TMDB."""


class FilmeNaoEncontrado(ErroTMDB):
    """404: o tmdb_id não existe."""


class LimitePedidos(ErroTMDB):
    """429: demasiados pedidos seguidos."""


class TMDBIndisponivel(ErroTMDB):
    """Sem rede, timeout ou erro 5xx do lado da TMDB."""


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------
class ClienteTMDB:
    """Faz os pedidos à TMDB e devolve modelos (≈ um serviço com HttpClient tipado em .NET).

    Uso:
        with ClienteTMDB.da_config() as tmdb:
            pagina = tmdb.pesquisar("Matrix")
            filme = tmdb.detalhe(603)

    O `with` fecha as ligações no fim (≈ `using` em C#).
    """

    def __init__(
        self,
        token: str,
        lingua: str = LINGUA_PADRAO,
        transport: httpx2.BaseTransport | None = None,
    ) -> None:
        # O parâmetro `transport` só é usado nos testes, para simular respostas sem
        # internet (≈ injetar um HttpMessageHandler falso num HttpClient em C#).
        if not token:
            raise TokenInvalido("Falta o TMDB_API_TOKEN no .env.")
        self.lingua = lingua
        self._http = httpx2.Client(
            base_url=URL_BASE,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=10.0,
            transport=transport,
        )

    @classmethod
    def da_config(cls, settings: Settings | None = None) -> Self:
        """Cria o cliente com o token do .env (≈ um método de fábrica estático)."""
        settings = settings or get_settings()
        return cls(settings.tmdb_api_token.get_secret_value().strip())

    # --- Operações públicas -------------------------------------------------

    def pesquisar(self, titulo: str, pagina: int = 1) -> PaginaPesquisa:
        """Pesquisa filmes por título. Devolve uma página (20 filmes no máximo)."""
        titulo = titulo.strip()
        if not titulo:
            # Não vale a pena gastar um pedido: devolvemos uma página vazia.
            return PaginaPesquisa(pagina=1, total_paginas=0, total_resultados=0, filmes=[])
        if not 1 <= pagina <= PAGINA_MAXIMA:
            raise ValueError(f"A página tem de estar entre 1 e {PAGINA_MAXIMA}.")

        dados = self._get(
            "/search/movie",
            {"query": titulo, "page": pagina, "language": self.lingua, "include_adult": "false"},
        )
        return PaginaPesquisa.model_validate(dados)

    def detalhe(self, tmdb_id: int) -> FilmeDetalhe:
        """Ficha completa de um filme. Se a sinopse vier vazia em pt-PT, usa a inglesa."""
        filme = FilmeDetalhe.model_validate(
            self._get(f"/movie/{tmdb_id}", {"language": self.lingua})
        )
        if not filme.sinopse and self.lingua != LINGUA_ALTERNATIVA:
            alternativo = self._get(f"/movie/{tmdb_id}", {"language": LINGUA_ALTERNATIVA})
            # model_copy(update=...) cria uma cópia com um campo alterado (≈ `with` dos records em C#).
            filme = filme.model_copy(update={"sinopse": alternativo.get("overview") or ""})
        return filme

    # --- Detalhes internos --------------------------------------------------

    def _get(self, caminho: str, params: dict) -> dict:
        """Faz um GET e traduz os erros HTTP para as nossas exceções."""
        try:
            resposta = self._http.get(caminho, params=params)
        except httpx2.TimeoutException as erro:
            raise TMDBIndisponivel("A TMDB demorou demasiado a responder.") from erro
        except httpx2.RequestError as erro:
            raise TMDBIndisponivel(f"Sem ligação à TMDB: {erro}") from erro

        codigo = resposta.status_code
        if codigo == 200:
            return resposta.json()
        if codigo == 401:
            raise TokenInvalido("A TMDB recusou o token (confirma o TMDB_API_TOKEN no .env).")
        if codigo == 404:
            raise FilmeNaoEncontrado(f"Não existe nenhum filme em {caminho}.")
        if codigo == 429:
            espera = resposta.headers.get("Retry-After", "alguns")
            raise LimitePedidos(f"Demasiados pedidos à TMDB; tenta de novo daqui a {espera} segundos.")
        if codigo >= 500:
            raise TMDBIndisponivel(f"A TMDB respondeu com erro {codigo}.")
        raise ErroTMDB(f"Resposta inesperada da TMDB: {codigo}.")

    def fechar(self) -> None:
        self._http.close()

    # __enter__/__exit__ permitem usar o cliente num `with` (≈ implementar IDisposable).
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_) -> None:
        self.fechar()
