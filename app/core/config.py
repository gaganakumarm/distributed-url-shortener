from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Distributed URL Shortener"
    environment: str = "development"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60

    database_url: str = "postgresql+asyncpg://urluser:urlpass@localhost:5432/urldb"
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600

    base_url: str = "http://localhost"
    short_code_length: int = 8
    api_instance: str = "api"
    auth_rate_limit_per_minute: int = 30
    write_rate_limit_per_minute: int = 120
    redirect_rate_limit_per_minute: int = 600

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.environment.lower() in {"production", "prod"}:
            if self.secret_key in {"change-me", "change-me-to-a-long-random-secret"} or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be a unique value of at least 32 characters in production")
        if not 4 <= self.short_code_length <= 32:
            raise ValueError("SHORT_CODE_LENGTH must be between 4 and 32")
        return self


settings = Settings()
