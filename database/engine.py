from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL
from sqlalchemy import text
from database.models import Base

# DATABASE_URL is now postgresql+asyncpg://... imported from config

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Auto-migration for existing tables (simple check)
    # We can use direct SQL to ensure columns exist if we are not using full Alembic
    async with engine.connect() as conn:
        await conn.execute(text("ALTER TABLE groups ADD COLUMN IF NOT EXISTS is_channel INTEGER DEFAULT 0;"))
        await conn.execute(text("ALTER TABLE schedule_times ADD COLUMN IF NOT EXISTS is_recurring INTEGER DEFAULT 1;"))
        await conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS name VARCHAR;"))
        await conn.commit()
