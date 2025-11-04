import os
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    DATABASE_URL: str = str
    REDIS_URL: str = "redis://redis:6379/0"

    JWT_SECRET : str
    ACCESS_TOKEN_EXPIRES : int = 900
    REFRESH_TOKEN_EXPIRES : int = 1209600

    ADMIN_USERNAME : str
    ADMIN_PASSWORD : str

    GOOGLE_PROJECT_ID : str
    BQ_DATASET_DEFAULT : str
    BQ_TABLE_DEFAULT : str
    VERTEX_MODEL : str
    VERTEX_LOCATION : str

    class Config:
        env_file = ".env"

settings = Settings()
