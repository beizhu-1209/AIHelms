from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库连接（可直接设置 DATABASE_URL，或由下面的变量拼接）
    database_url: str = ""
    postgres_user: str = "aihelms"
    postgres_password: str = "aihelms"
    postgres_db: str = "aihelms"
    db_host: str = "localhost"
    db_port: int = 5432

    # Redis 连接（可直接设置 REDIS_URL，或由下面的变量拼接）
    redis_url: str = ""
    redis_password: str = "aihelms"
    redis_host: str = "localhost"
    redis_port: int = 6379

    # LiteLLM（可直接设置 LITELLM_URL，或由下面的变量拼接）
    litellm_url: str = ""
    litellm_host: str = "localhost"
    litellm_port: int = 4000
    litellm_master_key: str = ""

    # 日志
    log_level: str = "WARNING"

    # 应用
    secret_key: str = "dev-secret-key"
    access_token_expire_minutes: int = 60 * 24
    super_admin_password: str = "admin123"

    # Gunicorn
    gunicorn_workers: int = 0
    gunicorn_timeout: int = 120
    gunicorn_keepalive: int = 5
    gunicorn_max_requests: int = 1000
    gunicorn_max_requests_jitter: int = 50
    gunicorn_loglevel: str = "info"

    # Celery
    celery_worker_concurrency: int = 0
    celery_loglevel: str = "info"
    celery_prefetch_multiplier: int = 1

    @model_validator(mode="after")
    def build_urls(self) -> "Settings":
        if not self.database_url:
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.db_host}:{self.db_port}/{self.postgres_db}"
            )
        if not self.redis_url:
            self.redis_url = (
                f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
            )
        if not self.litellm_url:
            self.litellm_url = f"http://{self.litellm_host}:{self.litellm_port}"
        return self

    class Config:
        env_file = "../.env"
        extra = "ignore"


settings = Settings()
