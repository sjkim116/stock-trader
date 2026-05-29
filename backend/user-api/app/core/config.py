"""
Configuration settings for the application.

Two PostgreSQL endpoints are configured separately:

* OLTP — AWS RDS PostgreSQL. Backing the OLTP schema in
  ``database/schema_oltp.sql`` (users, accounts, orders, ...).
* Time-series — self-managed TimescaleDB on EC2 (see
  ``infrastructure/terraform/modules/timescaledb_ec2``). Backs the
  ``market_data`` / ``quote_data`` hypertables in
  ``database/schema_timeseries.sql``.

In local docker-compose both DSNs resolve to the same container; in cloud
they point to different hosts.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    PROJECT_NAME: str = "AlgoTrader Pro User API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    AWS_REGION: str = "ap-northeast-2"

    API_V1_PREFIX: str = "/api/v1"

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ------------------------------------------------------------------ DB
    # OLTP (RDS PostgreSQL)
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "algotrader"
    DATABASE_USERNAME: str = "algotrader"
    DATABASE_PASSWORD: str = "dev_password_change_me"

    # Time-series (EC2 TimescaleDB)
    TIMESCALEDB_HOST: str = "localhost"
    TIMESCALEDB_PORT: int = 5432
    TIMESCALEDB_NAME: str = "algotrader"
    TIMESCALEDB_USERNAME: str = "algotrader"
    TIMESCALEDB_PASSWORD: str = "dev_password_change_me"

    # Pool sizing applies independently to each engine.
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT_SECONDS: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 1800

    # SQL echo is helpful while developing endpoints; keep off in tests/prod.
    DB_ECHO: bool = False

    # ---------------------------------------------------------- Paper trading
    # When set, the in-memory PaperBroker writes through to the OLTP DB
    # so positions / cash / fills survive process restarts. Leave unset
    # for ephemeral test runs and fresh local stacks.
    PAPER_TRADING_USER_ID: Optional[UUID] = None

    # ------------------------------------------------------------------ Redis
    REDIS_URL: str = "redis://:dev_password_change_me@localhost:6379"
    REDIS_TTL: int = 3600

    # ------------------------------------------------------------------ Auth
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-this-in-production",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    COGNITO_USER_POOL_ID: str = ""
    COGNITO_CLIENT_ID: str = ""
    COGNITO_REGION: str = "ap-northeast-2"

    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    # --------------------------------------------------------- URL builders
    @staticmethod
    def _async_url(user: str, password: str, host: str, port: int, name: str) -> str:
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"

    @staticmethod
    def _sync_url(user: str, password: str, host: str, port: int, name: str) -> str:
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

    @property
    def oltp_async_url(self) -> str:
        return self._async_url(
            self.DATABASE_USERNAME,
            self.DATABASE_PASSWORD,
            self.DATABASE_HOST,
            self.DATABASE_PORT,
            self.DATABASE_NAME,
        )

    @property
    def oltp_sync_url(self) -> str:
        return self._sync_url(
            self.DATABASE_USERNAME,
            self.DATABASE_PASSWORD,
            self.DATABASE_HOST,
            self.DATABASE_PORT,
            self.DATABASE_NAME,
        )

    @property
    def ts_async_url(self) -> str:
        return self._async_url(
            self.TIMESCALEDB_USERNAME,
            self.TIMESCALEDB_PASSWORD,
            self.TIMESCALEDB_HOST,
            self.TIMESCALEDB_PORT,
            self.TIMESCALEDB_NAME,
        )

    @property
    def ts_sync_url(self) -> str:
        return self._sync_url(
            self.TIMESCALEDB_USERNAME,
            self.TIMESCALEDB_PASSWORD,
            self.TIMESCALEDB_HOST,
            self.TIMESCALEDB_PORT,
            self.TIMESCALEDB_NAME,
        )


settings = Settings()
