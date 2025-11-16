from pydantic_settings import BaseSettings
from typing import List
from pydantic import field_validator
from pathlib import Path


class Settings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_minutes: int = 60 * 24 * 7
    database_url: str = "sqlite:///./pokedex.db"
    cors_origins: List[str] = []

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_file = str(Path(__file__).resolve().parent.parent / ".env")  # ✅ ruta absoluta
        env_file_encoding = "utf-8"


settings = Settings()
