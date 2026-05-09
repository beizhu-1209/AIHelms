from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://aihelms:changeme@localhost:5432/aihelms"
    redis_url: str = "redis://:changeme@localhost:6379/0"
    litellm_url: str = "http://localhost:4000"
    litellm_master_key: str = ""
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

    class Config:
        env_file = ".env"


settings = Settings()
