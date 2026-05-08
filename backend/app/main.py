"""
Zentro Leads — FastAPI Application Entry Point
Port: 8001
"""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.config import settings
from app.database import engine, Base
from app.rate_limiter import limiter
from app.admin.routes import router as admin_router
from app.analytics.routes import router as analytics_router
from app.auth.routes import router as auth_router
from app.billing.routes import router as billing_router
from app.icp.routes import router as icp_router
from app.jobs.routes import router as jobs_router
from app.leads.routes import router as leads_router
from app.settings.routes import router as settings_router
from app.pipeline.routes import router as pipeline_router
from app.scheduler import start_scheduler, shutdown_scheduler
from app.search.elasticsearch_client import ensure_leads_index, close_client as close_es
from app.search.pinecone_client import get_pinecone_index as _pinecone_connect


# ── Lifespan ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    start_scheduler()
    await ensure_leads_index()
    # Pinecone — optional; never crash startup if key is missing
    try:
        if settings.PINECONE_API_KEY:
            idx = await _pinecone_connect()
            if idx is not None:
                logger.info("Pinecone connected")
            else:
                logger.warning("Pinecone: key present but index init failed")
        else:
            logger.info("Pinecone not configured — skipping")
    except Exception as _exc:
        logger.warning(f"Pinecone startup check failed: {_exc}")
    yield
    shutdown_scheduler()
    await close_es()
    logger.info("Shutting down Zentro Leads")


# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered lead generation platform",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)
app.state.limiter = limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "https://leads.zentro.io",
        "https://app.zentro-leads.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(billing_router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(icp_router,  prefix="/api/v1/icp",  tags=["icp"])
app.include_router(leads_router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(settings_router,  prefix="/api/v1/settings",  tags=["settings"])
app.include_router(pipeline_router,  prefix="/api/v1/pipeline",  tags=["pipeline"])
app.include_router(jobs_router, tags=["jobs"])
app.include_router(admin_router, prefix="/api/v1", tags=["admin"])


# ── Health Check ─────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for Docker + Railway + Azure."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "jobs": 6,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
