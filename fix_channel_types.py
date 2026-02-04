import asyncio
from aiogram import Bot
from sqlalchemy import select
from database.engine import AsyncSessionLocal
from database.models import Group
from config import BOT_TOKEN

async def fix_types():
    bot = Bot(token=BOT_TOKEN)
    async with AsyncSessionLocal() as session:
        stmt = select(Group)
        res = await session.execute(stmt)
        groups = res.scalars().all()
        
        for g in groups:
            try:
                chat = await bot.get_chat(g.telegram_id)
                print(f"Checking {g.title} ({g.telegram_id})... Type: {chat.type}")
                
                is_channel = 1 if chat.type == "channel" else 0
                if g.is_channel != is_channel:
                    print(f"Updating {g.title}: is_channel {g.is_channel} -> {is_channel}")
                    g.is_channel = is_channel
                    session.add(g)
                else:
                    print(f"{g.title} is correct.")
            except Exception as e:
                print(f"Failed to check {g.title}: {e}")
                
        await session.commit()
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(fix_types())
