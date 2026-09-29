"""
Trim — Database Engine & Session

Configura o SQLAlchemy async para PostgreSQL.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.backend.config import settings

# ── Engine assíncrono ────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# ── Session factory ──────────────────────────────────────
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base declarativa ─────────────────────────────────────
class Base(DeclarativeBase):
    """Base para todos os models do Trim."""
    pass


# ── Dependency injection (FastAPI) ───────────────────────
async def get_db() -> AsyncSession:
    """
    Gera uma sessão de banco de dados por request.
    Uso: endpoint(db: AsyncSession = Depends(get_db))
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
