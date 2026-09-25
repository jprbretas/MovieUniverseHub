"""Integração com a API da TMDB.

Parte 2a: modelos (os "DTOs") que representam as respostas da TMDB.
Parte 2b (a seguir): o ClienteTMDB que faz os pedidos HTTP.

Os campos da TMDB estão em inglês (title, vote_count...). Nos nossos modelos usamos
nomes em português e ligamo-los ao JSON com `alias`, tal como o [JsonPropertyName]
em C#. Assim o resto da aplicação nunca precisa de saber como a TMDB chama as coisas.

Só declaramos os campos de que precisamos: o Pydantic ignora os restantes
(ex.: o campo não documentado "softcore" que apareceu nas respostas reais).
"""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

URL_IMAGENS = "https://image.tmdb.org/t/p/w500"  # base + tamanho (500 px de largura)


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
        validate_by_alias=True,  # lê o JSON da TMDB pelos nomes em inglês (alias)...
        validate_by_name=True,   # ...e também aceita os nomes em português (útil nos testes)
        extra="ignore",          # campos que não declarámos são descartados
    )


class Genero(ModeloTMDB):
    id: int
    nome: str = Field(alias="name")


class FilmeResumo(ModeloTMDB):
    """Um filme como aparece nos resultados de pesquisa (/search/movie)."""

    tmdb_id: int = Field(alias="id")
    titulo: str = Field(alias="title")
    titulo_original: str = Field(default="", alias="original_title")
    data_estreia: date | None = Field(default=None, alias="release_date")
    poster_path: str | None = Field(default=None, alias="poster_path")
    media_votos: float = Field(default=0.0, alias="vote_average")
    num_votos: int = Field(default=0, alias="vote_count")

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

    sinopse: str = Field(default="", alias="overview")
    generos: list[Genero] = Field(default_factory=list, alias="genres")
    duracao_min: int | None = Field(default=None, alias="runtime")

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

    pagina: int = Field(alias="page")
    total_paginas: int = Field(alias="total_pages")
    total_resultados: int = Field(alias="total_results")
    filmes: list[FilmeResumo] = Field(alias="results")
