from functools import lru_cache
from typing import Literal

from pydantic import Field
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
    timezone: str = "Asia/Jerusalem"
    max_dispatches: int = 6
    max_tool_calls: int = 8
    lease_seconds: int = 900
    heartbeat_seconds: int = 60
    run_timeout_seconds: int = 600
    step_timeout_seconds: int = 120
    http_timeout_seconds: float = 30.0
    http_connect_timeout_seconds: float = 15.0
    log_level: str = "INFO"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    variant: Literal["single", "rules", "llm"] = "rules"


@lru_cache
def get_settings() -> Settings:
    return Settings()
