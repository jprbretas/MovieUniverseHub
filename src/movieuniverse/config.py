"""Configuração da aplicação, lida do ficheiro .env.

Equivalente C#: appsettings.json + IOptions<T>. O pydantic-settings lê as
variáveis de ambiente (e o ficheiro .env) e valida-as contra os tipos declarados.
"""
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
        extra="ignore",         # variáveis desconhecidas no .env não dão erro
    )

    # SecretStr esconde o valor em prints/logs: aparece "**********".
    tmdb_api_token: SecretStr = SecretStr("")
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True  # reinicia ao gravar um .py; o F5 do VS Code desliga-o (ver launch.json)
    # Ficheiro SQLite em dados/ (≈ a connection string do appsettings.json).
    database_url: str = f"sqlite:///{(RAIZ_PROJETO / 'dados' / 'movieuniverse.db').as_posix()}"

    @property
    def tmdb_configurada(self) -> bool:
        """True se o token da TMDB foi preenchido (sem nunca expor o valor)."""
        return bool(self.tmdb_api_token.get_secret_value().strip())


@lru_cache
def get_settings() -> Settings:
    """Devolve sempre a mesma instância (≈ registar como Singleton no DI do .NET)."""
    return Settings()
