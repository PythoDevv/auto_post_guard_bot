from aiogram import Bot
from config import ADMINS

async def on_startup_notify(bot: Bot):
    for admin in ADMINS:
        try:
            await bot.send_message(admin, "Bot started!")
        except Exception as err:
            print(f"Failed to notify admin {admin}: {err}")
