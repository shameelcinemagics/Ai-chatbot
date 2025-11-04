from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: Optional[str] = None

    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"

    JWT_ACCESS_SECRET: str
    JWT_REFRESH_SECRET: str
    JWT_ISSUER: str
    JWT_AUDIENCE: str
    JWT_ACCESS_TTL_MIN: int = 15
    JWT_REFRESH_TTL_DAYS: int = 30

    COOKIE_SECURE: bool = False
    COOKIE_DOMAIN: Optional[str] = None

    GCP_PROJECT: str
    BQ_DATASET: str
    BQ_DEFAULT_TABLE: str
    VERTEX_MODEL: str
    VERTEX_REGION: str

    ADMIN_EMAIL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("COOKIE_DOMAIN")
    def _empty_domain_as_none(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value.strip() == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
