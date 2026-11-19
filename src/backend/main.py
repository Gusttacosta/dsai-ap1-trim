"""
Trim — FastAPI Application Entry Point

Configura o app FastAPI com CORS, routers e lifecycle events.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import settings


from src.backend.database import engine, Base

logger = logging.getLogger(__name__)
LOG_HANDLER_NAME = "trim-backend"


def configure_logging() -> None:
    """Mostra no terminal os logs INFO do backend, no formato do uvicorn.

    O uvicorn só configura os loggers dele; sem isto, `logger.info` não aparece. O handler é
    adicionado uma vez só, e o logger raiz não muda.
    """
    app_logger = logging.getLogger("src.backend")
    app_logger.setLevel(logging.INFO)
    if not any(h.get_name() == LOG_HANDLER_NAME for h in app_logger.handlers):
        handler = logging.StreamHandler()
        handler.set_name(LOG_HANDLER_NAME)
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
        app_logger.addHandler(handler)


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook: executa na inicialização e no shutdown do app."""
    # ── Startup ──
    # Mensagens só em ASCII: o console do Windows (cp1252) não codifica emojis (#2).
    logger.info(
        "%s backend iniciando (ambiente: %s, debug: %s)",
        settings.app_name, settings.app_env, settings.debug,
    )
    logger.info("Verificando/criando tabelas no banco de dados...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Banco de dados pronto.")

    yield
    # ── Shutdown ──
    logger.info("%s backend encerrando.", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="Plataforma completa de gestão para barbearias.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check ─────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Verifica se o backend está rodando e informa o commit em produção."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "0.1.0",
        "commit": settings.render_git_commit,
    }


# ── API Root ─────────────────────────────────────────────
@app.get("/api", tags=["System"])
async def api_root():
    """Informações gerais da API."""
    return {
        "app": settings.app_name,
        "description": "Plataforma completa de gestão para barbearias",
        "version": "0.1.0",
        "docs": "/docs",
    }


# ──────────────────────────────────────────────────────────
from src.backend.modules.auth.router import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

from src.backend.modules.barbers.router import router as barbers_router
app.include_router(barbers_router, prefix="/api/barbers", tags=["Barbers"])

from src.backend.modules.services.router import router as services_router
app.include_router(services_router, prefix="/api/services", tags=["Services"])

from src.backend.modules.appointments.router import router as appointments_router
app.include_router(appointments_router, prefix="/api/appointments", tags=["Appointments"])

from src.backend.modules.products.router import router as products_router
app.include_router(products_router, prefix="/api/products", tags=["Products"])

from src.backend.modules.subscriptions.router import router as subscriptions_router
app.include_router(subscriptions_router, prefix="/api/subscriptions", tags=["Subscriptions"])

from src.backend.modules.finance.router import router as finance_router
app.include_router(finance_router, prefix="/api/finance", tags=["Finance"])

from src.backend.modules.expenses.router import router as expenses_router
app.include_router(expenses_router, prefix="/api/expenses", tags=["Expenses"])

from src.backend.modules.dashboard.router import router as dashboard_router
app.include_router(dashboard_router, prefix="/api/reports", tags=["Reports & Dashboard"])

from src.backend.modules.walkin.router import router as walkin_router
app.include_router(walkin_router, prefix="/api/queue", tags=["Walk-in Queue"])

from src.backend.modules.gallery.router import router as gallery_router
app.include_router(gallery_router, prefix="/api/gallery", tags=["Gallery"])

from src.backend.modules.loyalty.router import router as loyalty_router
app.include_router(loyalty_router, prefix="/api/loyalty", tags=["Loyalty"])

from src.backend.modules.notifications.router import router as notifications_router
app.include_router(notifications_router, prefix="/api/notifications", tags=["Notifications"])

from src.backend.modules.dev_router import router as dev_router
app.include_router(dev_router, prefix="/api/dev", tags=["Dev"])

# ──────────────────────────────────────────────────────────
