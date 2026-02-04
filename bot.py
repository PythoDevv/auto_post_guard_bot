import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from middlewares.db import DbSessionMiddleware
from middlewares.spam_filter import SpamFilterMiddleware
from services.scheduler import setup_scheduler
from database.engine import init_db
from utils.notify_admins import on_startup_notify

# Logger setup
logging.basicConfig(level=logging.INFO)

async def main():
    logger = logging.getLogger(__name__)
    logger.info("Starting bot...")

    # Validate token
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set in environment or config.py")
        return

    # Initialize Database
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Middlewares
    dp.update.middleware(DbSessionMiddleware())
    dp.message.middleware(SpamFilterMiddleware())

    # Routers
    # We will import and include routers here. 
    # For now, to ensure the code runs without error before handlers are fully implemented,
    # we will comment them out or assume they exist.
    # To follow the plan, I will create basic init files next so we can import them.
    from handlers import users_router, groups_router, admin_router
    dp.include_router(users_router)
    dp.include_router(groups_router)
    dp.include_router(admin_router)

    # Scheduler
    setup_scheduler(bot)

    # Delete webhook to run polling
    await bot.delete_webhook(drop_pending_updates=True)

    # Startup Notification
    await on_startup_notify(bot)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
