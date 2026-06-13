from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
import secrets
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    PROJECT_NAME: str = "SuccessCore HR"
    VERSION:      str = "1.0.0"
    API_V1_STR:   str = "/api/v1"

    # ── Security ───────────────────────────────────────────────────────────────
    SECRET_KEY:    str = os.getenv("SECRET_KEY", "")
    ENCRYPTION_KEY: str = ""
    DEBUG_MODE:     bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.SECRET_KEY in ("", "supersecretfallbackkeyforlocallogin123!", "changeme"):
            raise ValueError(
                "CRITICAL: SECRET_KEY environment variable is not set or is using an insecure default. "
                "Set a strong SECRET_KEY via environment variable or .env file."
            )
        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")

    # ── Database ──────────────────────────────────────────────────────────────
    POSTGRES_SERVER:   str = "localhost"
    POSTGRES_USER:     str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB:       str = "successcore"
    POSTGRES_PORT:     str = "5432"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = ""  # Full connection URL (e.g. Upstash: redis://default:password@host:port)

    # ── Auth0 ─────────────────────────────────────────────────────────────────
    AUTH0_DOMAIN:       str = "your-tenant.auth0.com"
    AUTH0_CLIENT_ID:    str = "your-client-id"
    AUTH0_API_AUDIENCE: str = "https://api.successcore.com"
    AUTH0_ISSUER:       str = "https://your-tenant.auth0.com/"
    AUTH0_ALGORITHMS:   str = "RS256"

    # ── Frontend / CORS ───────────────────────────────────────────────────────
    # Ej. producción: "https://app.successcore.com"
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Slack Integration ─────────────────────────────────────────────────────
    SLACK_SIGNING_SECRET: str = ""
    SLACK_BOT_TOKEN: str = ""
    SLACK_CLIENT_ID: str = ""
    SLACK_CLIENT_SECRET: str = ""

    # ── Courier API (Notificaciones) ──────────────────────────────────────────
    COURIER_AUTH_TOKEN: str = "pk_test_replace_me_with_courier_key"

    # ── AI Reseller / BYOK Keys ───────────────────────────────────────────────
    OPENAI_API_KEY:    str = ""
    GEMINI_API_KEY:    str = ""
    OPENROUTER_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROK_API_KEY:      str = ""
    GROQ_API_KEY:      str = ""

    # ── SMTP / Email ──────────────────────────────────────────────────────────
    SMTP_HOST:          Optional[str] = None
    SMTP_PORT:          Optional[int] = 587
    SMTP_USER:          Optional[str] = None
    SMTP_PASSWORD:      Optional[str] = None
    EMAILS_FROM_EMAIL:  Optional[str] = None

    # ── DocuSign Integration ──────────────────────────────────────────────────
    DOCUSIGN_ACCOUNT_ID: str = ""
    DOCUSIGN_INTEGRATION_KEY: str = ""
    DOCUSIGN_USER_ID: str = ""
    DOCUSIGN_PRIVATE_KEY_PATH: str = ""
    DOCUSIGN_BASE_URL: str = "https://demo.docusign.net/restapi"

    # ── Propiedades derivadas ─────────────────────────────────────────────────
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            uri = self.DATABASE_URL
            if uri.startswith("postgres://"):
                uri = uri.replace("postgres://", "postgresql+asyncpg://", 1)
            elif uri.startswith("postgresql://"):
                uri = uri.replace("postgresql://", "postgresql+asyncpg://", 1)
                
            # asyncpg doesnt support sslmode=require in the url, it fails. We remove it.
            if "?" in uri:
                uri = uri.split("?")[0]
                
            return uri
            
        # Fallback to local postgres
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "password")
        server = os.getenv("POSTGRES_SERVER", "localhost")
        db = os.getenv("POSTGRES_DB", "successcore")
        return f"postgresql+asyncpg://{user}:{password}@{server}/{db}"

    @property
    def SYNC_DATABASE_URI(self) -> str:
        # Return sync version of the URI (psycopg2)
        async_uri = self.SQLALCHEMY_DATABASE_URI
        return async_uri.replace("+asyncpg", "")

    @property
    def REDIS_URI(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )


settings = Settings()
