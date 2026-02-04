from aiogram import Router
from .group_handlers import router as group_router

router = Router()
router.include_router(group_router)
