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

    @property
    def database_url_async(self) -> str:
        """Deriva a URL assíncrona a partir da DATABASE_URL (ex.: postgresql:// do Render)."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def database_url_sync(self) -> str:
        """Deriva a URL síncrona a partir da DATABASE_URL (ex.: postgresql:// do Render)."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        return url

    # ── JWT / Auth ───────────────────────────────────────
    secret_key: str = "dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 horas

    # ── Seed (rotas /api/dev) ────────────────────────────
    # Vazias = rotas de seed desligadas (404) e admin de demonstração não criado.
    seed_secret: str = ""
    seed_admin_password: str = ""
    # Vazia = barbeiro e cliente de demonstração ficam com senha aleatória (sem login).
    seed_demo_password: str = ""

    # ── Agendamento ──────────────────────────────────────
    # Fuso em que o expediente (WorkSchedule) e as datas da tela são interpretados.
    # O banco guarda sempre UTC.
    shop_timezone: str = "America/Sao_Paulo"
    # Antecedência mínima para agendar (0 = só proíbe horários que já passaram) e
    # quantos dias à frente se pode agendar. Provisórios até a resposta do cliente (#15).
    booking_min_lead_minutes: int = 0
    booking_max_days_ahead: int = 30

    # ── CORS ─────────────────────────────────────────────
    # Só origens locais. Em produção, CORS_ORIGINS recebe a URL do frontend.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Deploy ───────────────────────────────────────────
    # O Render define RENDER_GIT_COMMIT em cada deploy; fora dele, "local".
    render_git_commit: str = "local"

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
