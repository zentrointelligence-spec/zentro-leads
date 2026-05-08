from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    # ── App ──────────────────────────────────────────────────
    APP_NAME: str = "LeadRadar"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

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
    OPENAI_API_KEY: str = ""

    # ── Gemini (bulk normalization at low cost) ───────────────
    GOOGLE_GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash-8b"
    # gemini-1.5-flash-8b = cheapest Gemini model; ideal for high-volume
    # normalization tasks (industry, job title, location, insurance need).
    # ~$0.0375 per 1M input tokens — orders of magnitude cheaper than Claude.

    # ── Google Sheets export ──────────────────────────────────────
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""
    # Full JSON string of the service account key file

    # ── Vector Search (Pinecone) ──────────────────────────────
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "zentro-leads"

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

    # ── Payments — Stripe ────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_GROWTH: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_AGENCY: str = ""

    # ── Payments — Billplz FPX (Malaysian market) ────────────
    BILLPLZ_API_KEY: str = ""
    BILLPLZ_COLLECTION_ID: str = ""
    BILLPLZ_X_SIGNATURE: str = ""
    BILLPLZ_SANDBOX: bool = True

    # ── Payments — Razorpay UPI (Indian market) ───────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    # Get keys from https://dashboard.razorpay.com/app/keys
    # Sandbox URL: https://www.billplz-sandbox.com/api/v3
    # Production URL: https://www.billplz.com/api/v3

    # ── URLs ─────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3001"
    BACKEND_URL: str = "http://localhost:8001"
    # BACKEND_URL is used for Billplz callback_url (must be publicly reachable)

    # ── n8n ──────────────────────────────────────────────────
    N8N_WEBHOOK_URL: str = "http://localhost:5678"
    N8N_API_KEY: str = ""

    # ── Search ───────────────────────────────────────────────
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # ── Cache TTLs (seconds) ─────────────────────────────────
    CACHE_TTL_LEADS: int = 3600       # 1 hour
    CACHE_TTL_EMAIL: int = 604800     # 7 days
    CACHE_TTL_ICP: int = 86400        # 24 hours

    # ── Rate Limiting ────────────────────────────────────────
    SCRAPE_DELAY_MIN: float = 1.5
    SCRAPE_DELAY_MAX: float = 4.0
    # SlowAPI storage URI. When empty: if DEBUG=true use memory:// (no Redis required
    # locally); otherwise REDIS_URL. Set explicitly e.g. redis://... to override.
    RATE_LIMIT_STORAGE_URI: str = ""

    # ── Admin ────────────────────────────────────────────────
    ADMIN_PHONE: str = ""
    ADMIN_EMAIL: str = ""

    # ── ML Scoring Pipeline ──────────────────────────────────
    XGBOOST_MODEL_PATH: str = "models/lead_scorer.json"
    MLFLOW_TRACKING_URI: str = "sqlite:///mlflow.db"
    MODEL_RETRAIN_THRESHOLD: int = 100
    # Minimum new feedback records before automatic retrain kicks in

    # ── Cookie Security ──────────────────────────────────────
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
