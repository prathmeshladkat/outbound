
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Payer Voice Agent"
    environment: str = "development"

    database_url: str
    redis_url: str

    deepgram_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""

    exotel_api_key: str = ""
    exotel_api_token: str = ""
    exotel_sid: str = ""
    exotel_subdomain: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
