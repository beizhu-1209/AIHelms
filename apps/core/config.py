from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://aihelms:changeme@localhost:5432/aihelms"
    redis_url: str = "redis://:changeme@localhost:6379/0"
    litellm_url: str = "http://localhost:4000"
    litellm_master_key: str = ""
    secret_key: str = "dev-secret-key"
    access_token_expire_minutes: int = 60 * 24

    class Config:
        env_file = ".env"


settings = Settings()
