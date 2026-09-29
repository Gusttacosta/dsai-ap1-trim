"""
Trim — Application Settings

Centraliza todas as configurações do backend via variáveis de ambiente.
Usa pydantic-settings para validação e tipagem automática.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais da aplicação Trim."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    app_name: str = "Trim"
    app_env: str = "development"
    debug: bool = True

    # ── Database ─────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/trim_db"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/trim_db"

    # ── JWT / Auth ───────────────────────────────────────
    secret_key: str = "dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 horas

    # ── CORS ─────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Server ───────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def cors_origins_list(self) -> list[str]:
        """Retorna as origens CORS como lista."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        """Verifica se está em ambiente de desenvolvimento."""
        return self.app_env == "development"


# Instância global de settings — importar de qualquer lugar
settings = Settings()
