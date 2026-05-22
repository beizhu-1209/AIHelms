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
    # 对外暴露给用户客户端的 LiteLLM 地址（自动由 NGINX_SERVER_NAME + LITELLM_PORT 拼接）
    litellm_public_url: str = ""
    nginx_server_name: str = "localhost"
    web_port: int = 80
    # 平台对外访问地址（自动由 NGINX_SERVER_NAME + WEB_PORT 拼接），用于生成 skill 下载链接等
    platform_public_url: str = ""

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

    # 文件存储（开发：项目根 ../data；生产容器内：/data）
    data_dir: str = "../data"
    skills_storage_dir: str = ""
    uploads_storage_dir: str = ""
    exports_storage_dir: str = ""

    # 管理员日志保留天数
    audit_log_retention_days: int = 180

    # LLM 调用日志同步与清理
    llm_log_sync_interval_minutes: int = 5
    llm_log_retention_days: int = 0  # 0 = 不清理

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
        if not self.litellm_public_url:
            # 用 NGINX_SERVER_NAME + LITELLM_PORT 拼接对外 LiteLLM 地址
            host = self.nginx_server_name.split()[0] if self.nginx_server_name else "localhost"
            self.litellm_public_url = f"http://{host}:{self.litellm_port}"
        if not self.platform_public_url:
            host = self.nginx_server_name.split()[0] if self.nginx_server_name else "localhost"
            port_suffix = "" if self.web_port == 80 else f":{self.web_port}"
            self.platform_public_url = f"http://{host}{port_suffix}"
        if not self.skills_storage_dir:
            self.skills_storage_dir = f"{self.data_dir}/skills"
        if not self.uploads_storage_dir:
            self.uploads_storage_dir = f"{self.data_dir}/uploads"
        if not self.exports_storage_dir:
            self.exports_storage_dir = f"{self.data_dir}/exports"
        return self

    class Config:
        env_file = "../.env"
        extra = "ignore"


settings = Settings()
