from .users import router as users_router
from .groups import router as groups_router
from .admin import router as admin_router

__all__ = [
    "users_router",
    "groups_router",
    "admin_router",
]
