from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    campus_timezone: str = "Asia/Kolkata"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "gemma4:e4b"
    ollama_timeout_seconds: int = Field(default=120, ge=1, le=600)

    @field_validator("campus_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("CAMPUS_TIMEZONE must be a valid IANA timezone.") from error
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
