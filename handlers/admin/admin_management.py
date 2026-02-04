from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User
from handlers.admin.states import AdminStates
from keyboards.inline import admin_kbs
from config import ADMINS

router = Router()

async def check_admin_permission(user_id: int, session: AsyncSession) -> bool:
    if user_id in ADMINS:
        return True
    
    stmt = select(User).where(User.telegram_id == user_id)
    res = await session.execute(stmt)
    user = res.scalars().first()
    
    if user and user.is_admin == 1:
        return True
    return False

@router.callback_query(F.data == "admin_management")
async def admin_management_menu(callback: types.CallbackQuery, session: AsyncSession):
    if not await check_admin_permission(callback.from_user.id, session):
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return

    # No unnecessary queries needed here, just show menu
    await callback.message.edit_text("Adminlarni Boshqarish Paneli", reply_markup=admin_kbs.admin_management_keyboard())

@router.callback_query(F.data == "list_admins")
async def list_admins(callback: types.CallbackQuery, session: AsyncSession):
    if not await check_admin_permission(callback.from_user.id, session):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    # We list users who are strictly is_admin=1 in DB. 
    # ADMINS in .env might not be in DB or have is_admin=0 (though logic tries to sync).
    stmt = select(User).where(User.is_admin == 1)
    res = await session.execute(stmt)
    admins = res.scalars().all()
    
    text = "Bot Adminlari:\n"
    for admin in admins:
        text += f"- {admin.full_name} (ID: {admin.telegram_id})\n"
    
    # Also list ENV admins if not in DB list?
    # User asked for "list admins". 
    # Let's just stick to DB admins as they are the managed ones.
        
    await callback.message.edit_text(text, reply_markup=admin_kbs.back_to_admin_management())

@router.callback_query(F.data == "add_admin")
async def start_add_admin(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    if not await check_admin_permission(callback.from_user.id, session):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
        
    await callback.message.edit_text("Admin qilish uchun foydalanuvchi Telegram ID sini yuboring.", reply_markup=admin_kbs.cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_new_admin_id)

@router.message(AdminStates.waiting_for_new_admin_id)
async def add_admin_handler(message: types.Message, state: FSMContext, session: AsyncSession):
    # Permission check again? Message handlers not triggered by buttons might bypass? 
    # State protects somewhat, but good practice.
    if not await check_admin_permission(message.from_user.id, session):
        await message.answer("Ruxsat yo'q.")
        return

    try:
        new_admin_id = int(message.text.strip())
    except ValueError:
        await message.answer("Noto'g'ri ID. Iltimos raqamli Telegram ID kiriting.")
        return

    stmt = select(User).where(User.telegram_id == new_admin_id)
    res = await session.execute(stmt)
    user = res.scalars().first()

    if not user:
        await message.answer("Foydalanuvchi bazada topilmadi. Ular avval botni ishga tushirishlari kerak.")
        return

    if user.is_admin == 1:
        await message.answer("Foydalanuvchi allaqachon admin.")
    else:
        user.is_admin = 1
        await session.commit()
        await message.answer(f"Foydalanuvchi {user.full_name} Adminga aylantirildi.")
    
    await state.clear()
    await message.answer("Adminlarni Boshqarish Paneli", reply_markup=admin_kbs.admin_management_keyboard())

@router.callback_query(F.data == "remove_admin")
async def start_remove_admin(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    if not await check_admin_permission(callback.from_user.id, session):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    await callback.message.edit_text("Adminlikdan olish uchun foydalanuvchi Telegram ID sini yuboring.", reply_markup=admin_kbs.cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_remove_admin_id)

@router.message(AdminStates.waiting_for_remove_admin_id)
async def remove_admin_handler(message: types.Message, state: FSMContext, session: AsyncSession):
    if not await check_admin_permission(message.from_user.id, session):
        await message.answer("Ruxsat yo'q.")
        return

    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("Noto'g'ri ID.")
        return

    stmt = select(User).where(User.telegram_id == target_id)
    res = await session.execute(stmt)
    user = res.scalars().first()

    if not user:
        await message.answer("Foydalanuvchi topilmadi.")
        return

    if user.is_admin == 0:
        await message.answer("Foydalanuvchi admin emas.")
    else:
        user.is_admin = 0
        await session.commit()
        await message.answer(f"Foydalanuvchi {user.full_name} Adminlikdan olib tashlandi.")
    
    await state.clear()
    await message.answer("Adminlarni Boshqarish Paneli", reply_markup=admin_kbs.admin_management_keyboard())
