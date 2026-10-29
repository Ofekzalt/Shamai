from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SHAMAI_",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://shamai:shamai@localhost:5432/shamai",
        validation_alias="DATABASE_URL",
    )
    neighborhoods: list[str] = Field(default_factory=list)
    timezone: str = "Asia/Jerusalem"
    max_dispatches: int = 6
    max_tool_calls: int = 8
    lease_seconds: int = 900
    heartbeat_seconds: int = 60
    run_timeout_seconds: int = 600
    step_timeout_seconds: int = 120

    @field_validator("neighborhoods", mode="before")
    @classmethod
    def parse_neighborhoods(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, list):
            return [str(part).strip() for part in value if str(part).strip()]
        return []


@lru_cache
def get_settings() -> Settings:
    return Settings()
