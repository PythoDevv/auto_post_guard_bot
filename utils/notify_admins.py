from aiogram import Bot
from config import ADMINS
from sqlalchemy import select
from database.models import User
from database.engine import AsyncSessionLocal

async def on_startup_notify(bot: Bot):
    # Ensure primary admin exists
    PRIMARY_ADMIN_ID = 935795577
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == PRIMARY_ADMIN_ID)
        res = await session.execute(stmt)
        user = res.scalars().first()
        
        if not user:
            # Create the user if they don't exist
            # Note: We might not have username/fullname if they haven't started bot, 
            # but we can fill placeholders or wait for them to start. 
            # Ideally we want them to be admin immediately.
            user = User(
                telegram_id=PRIMARY_ADMIN_ID,
                full_name="Primary Admin",
                username="admin",
                is_admin=1
            )
            session.add(user)
            await session.commit()
            print(f"Created primary admin {PRIMARY_ADMIN_ID}")
        else:
            if user.is_admin != 1:
                user.is_admin = 1
                await session.commit()
                print(f"Promoted primary admin {PRIMARY_ADMIN_ID}")

    for admin in ADMINS:
        try:
            await bot.send_message(admin, "Bot ishga tushdi!") # Translated to warnings
        except Exception as err:
            print(f"Failed to notify admin {admin}: {err}")
