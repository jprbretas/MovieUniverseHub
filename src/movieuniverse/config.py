"""Configuração da aplicação, lida do ficheiro .env e das variáveis de ambiente."""
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do repositório: src/movieuniverse/config.py -> sobe 3 níveis.
RAIZ_PROJETO = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Cada atributo corresponde a uma variável do .env (sem distinguir maiúsculas)."""

    model_config = SettingsConfigDict(
        env_file=RAIZ_PROJETO / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # "PORT=" vazio no .env -> usa o valor por omissão
        extra="ignore",
    )

    # SecretStr: o valor aparece como "**********" em prints e logs.
    tmdb_api_token: SecretStr = SecretStr("")
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    database_url: str = f"sqlite:///{(RAIZ_PROJETO / 'dados' / 'movieuniverse.db').as_posix()}"

    @property
    def tmdb_configurada(self) -> bool:
        """True se o token da TMDB foi preenchido (sem nunca expor o valor)."""
        return bool(self.tmdb_api_token.get_secret_value().strip())


@lru_cache
def get_settings() -> Settings:
    """Lê o .env uma só vez e devolve sempre a mesma instância."""
    return Settings()
