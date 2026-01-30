from aiogram import Router
from .admin_handlers import router as admin_router
from .superadmin import router as superadmin_router

router = Router()
router.include_router(admin_router)
router.include_router(superadmin_router)
