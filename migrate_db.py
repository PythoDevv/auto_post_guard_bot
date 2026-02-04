import asyncio
import asyncpg
from config import DATABASE_URL

async def migrate():
    # Parse the URL manually or assume standard format for asyncpg
    # postgresql+asyncpg://user:pass@host:port/dbname
    conn_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    conn = await asyncpg.connect(conn_url)
    try:
        await conn.execute("ALTER TABLE groups ADD COLUMN IF NOT EXISTS is_channel INTEGER DEFAULT 0;")
        print("Successfully added is_channel column.")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
