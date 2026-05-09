"""
数据库迁移管理

启动时自动执行 docker/db/migrations/ 下未执行的 SQL 文件。
迁移文件命名规则: NNN_描述.sql（如 001_add_avatar.sql）
按文件名排序执行，已执行的记录在 aihelms.schema_migrations 表中。
"""

import asyncio
import logging
from pathlib import Path

import asyncpg

from core.config import settings

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "docker" / "db" / "migrations"


async def run_migrations() -> None:
    """执行所有未执行的迁移文件"""
    conn = await asyncpg.connect(str(settings.DATABASE_URL))
    try:
        # 确保迁移记录表存在
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS aihelms.schema_migrations (
                version VARCHAR(128) PRIMARY KEY,
                executed_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # 获取已执行的迁移
        rows = await conn.fetch("SELECT version FROM aihelms.schema_migrations")
        executed = {row["version"] for row in rows}

        # 扫描迁移文件
        if not MIGRATIONS_DIR.exists():
            logger.info("migrations directory not found, skipping")
            return

        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

        for f in migration_files:
            version = f.stem
            if version in executed:
                continue

            logger.info(f"executing migration: {version}")
            sql = f.read_text(encoding="utf-8")
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO aihelms.schema_migrations (version) VALUES ($1)",
                version,
            )
            logger.info(f"migration completed: {version}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migrations())
