from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "automation-platform"
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    PROXY_CONFIGS_JSON: str = "[]"
    PROXY_HEALTHCHECK_URL: str = "https://example.com/"
    PROXY_HEALTHCHECK_TIMEOUT_MS: int = 5000
    AUTOMATION_RATE_LIMIT_PER_HOUR: int = 30
    COMPLIANCE_KILL_SWITCH: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
