"""Application configuration — everything comes from the environment."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "HireTrack API"
    # sqlite for local dev/tests, postgres in docker-compose / production
    database_url: str = "sqlite:///./hiretrack.db"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


settings = Settings()
