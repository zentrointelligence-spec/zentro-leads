from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────
    APP_NAME: str = "Zentro Leads"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── Auth ─────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # ── Database ─────────────────────────────────────────────
    POSTGRES_URL: str
    POSTGRES_URL_ASYNC: str

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str

    # ── ZIMS Integration ─────────────────────────────────────
    ZIMS_API_URL: str = ""
    ZIMS_INTERNAL_API_KEY: str = ""

    # ── AI ───────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""

    # ── Scraping ─────────────────────────────────────────────
    GOOGLE_MAPS_API_KEY: str = ""
    GOOGLE_SEARCH_API_KEY: str = ""
    GOOGLE_SEARCH_CX: str = ""
    ROTATING_PROXY_URL: str = ""

    # ── Email ────────────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@zentro-leads.io"

    # ── WhatsApp / SMS ───────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""

    # ── Payments ─────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_GROWTH: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_AGENCY: str = ""

    # ── n8n ──────────────────────────────────────────────────
    N8N_WEBHOOK_URL: str = "http://localhost:5678"
    N8N_API_KEY: str = ""

    # ── Cache TTLs (seconds) ─────────────────────────────────
    CACHE_TTL_LEADS: int = 3600       # 1 hour
    CACHE_TTL_EMAIL: int = 604800     # 7 days
    CACHE_TTL_ICP: int = 86400        # 24 hours

    # ── Rate Limiting ────────────────────────────────────────
    SCRAPE_DELAY_MIN: float = 1.5
    SCRAPE_DELAY_MAX: float = 4.0

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
