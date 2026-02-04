import asyncio
from sqlalchemy import text
from database.engine import engine

async def migrate():
    try:
        async with engine.begin() as conn:
            # Add is_channel to groups
            await conn.execute(text("ALTER TABLE groups ADD COLUMN IF NOT EXISTS is_channel INTEGER DEFAULT 0;"))
            
            # Add post_id to schedule_times
            await conn.execute(text("ALTER TABLE schedule_times ADD COLUMN IF NOT EXISTS post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE;"))
            
            # Add entities to posts
            await conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS entities TEXT;"))
            
        print("Migration successful!")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
