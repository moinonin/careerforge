"""Sprint 8 migration: add output_language, missing_keywords to generation_jobs."""

import asyncio
import sys

sys.path.insert(0, "/Users/nickrotich/Desktop/portfolio/projects/python/careerforge")

import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://careerforge:***@localhost:5432/careerforge")

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text


async def migrate():
    engine = create_async_engine(
        os.environ["DATABASE_URL"],
        echo=False,
    )
    async with engine.begin() as conn:
        # Add output_language column
        await conn.execute(
            text("ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS output_language VARCHAR(10) DEFAULT 'en' NOT NULL")
        )
        # Add missing_keywords column (JSON for SQLite/PostgreSQL compatibility)
        await conn.execute(
            text("ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS missing_keywords JSON")
        )
        await conn.commit()
    print("Migration complete!")


if __name__ == "__main__":
    asyncio.run(migrate())
