import os
from pydantic import BaseModel, Field, EmailStr
from functools import lru_cache

class Settings(BaseModel):
    # server
    APP_NAME: str = "analytics-chatbot"
    ENV: str = Field(default="production")
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: [])

    # db (Postgres)
    DATABASE_URL: str

    # JWT
    JWT_ACCESS_SECRET: str
    JWT_REFRESH_SECRET: str
    JWT_ISSUER: str = "analytics-chatbot"
    JWT_AUDIENCE: str = "analytics-frontend"
    JWT_ACCESS_TTL_MIN: int = 10
    JWT_REFRESH_TTL_DAYS: int = 30

    # cookies
    COOKIE_SECURE: bool = True
    COOKIE_DOMAIN: str | None = None

    # BigQuery / Vertex AI
    GCP_PROJECT: str
    BQ_DATASET: str
    BQ_DEFAULT_TABLE: str = "daily_events"
    VERTEX_REGION: str = "us-central1"
    VERTEX_MODEL: str = "gemini-1.5-pro"

    ADMIN_EMAIL: EmailStr = "admin@cinemagics.com"

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache
def get_settings() -> Settings:
    # Parse comma list for CORS
    origins = os.getenv("CORS_ORIGINS", "")
    os.environ["CORS_ORIGINS"] = ""  # keep env clean for pydantic
    s = Settings(_env_file=os.getenv("ENV_FILE", ".env"))
    if origins:
        s.CORS_ORIGINS = [o.strip() for o in origins.split(",") if o.strip()]
    return s
