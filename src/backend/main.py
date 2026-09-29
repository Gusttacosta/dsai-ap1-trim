"""
Trim — FastAPI Application Entry Point

Configura o app FastAPI com CORS, routers e lifecycle events.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook: executa na inicialização e no shutdown do app."""
    # ── Startup ──
    print(f"🚀 {settings.app_name} backend starting...")
    print(f"   Environment: {settings.app_env}")
    print(f"   Debug: {settings.debug}")
    yield
    # ── Shutdown ──
    print(f"👋 {settings.app_name} backend shutting down...")


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
    """Verifica se o backend está rodando."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "0.1.0",
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

# ──────────────────────────────────────────────────────────
