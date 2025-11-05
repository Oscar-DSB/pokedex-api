from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = "CHANGE_ME"      # ⬅️ usa .env
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24      # 24h
    refresh_token_expire_minutes: int = 60 * 24 * 7 # 7 días

    class Config:
        env_file = ".env"

settings = Settings()
