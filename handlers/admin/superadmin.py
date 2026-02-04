from aiogram import Router, types
from aiogram.filters import Command
from aiogram import F
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User
from services.excel import export_users_to_excel
from config import ADMINS

router = Router()

def is_superadmin(user_id: int) -> bool:
    return user_id in ADMINS

@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, session: AsyncSession):
    if not is_superadmin(message.from_user.id):
        return

    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("Foydalanish: /broadcast <xabar>")
        return

    stmt = select(User)
    res = await session.execute(stmt)
    users = res.scalars().all()
    
    count = 0
    for user in users:
        try:
            await message.bot.send_message(user.telegram_id, text)
            count += 1
        except Exception as e:
            print(f"Failed to send to {user.telegram_id}: {e}")
            
    await message.answer(f"Xabar yuborish tugadi. {count} foydalanuvchilarga yuborildi.")


@router.message(Command("export"))
async def cmd_export(message: types.Message, session: AsyncSession):
    if not is_superadmin(message.from_user.id):
        return

    await message.answer("Eksport qilinmoqda...")
    
    stmt = select(User)
    res = await session.execute(stmt)
    users = res.scalars().all()
    
    if not users:
        await message.answer("Foydalanuvchilar topilmadi.")
        return

    file_io = export_users_to_excel(users)
    file = types.BufferedInputFile(file_io.read(), filename="users.xlsx")
    
    await message.answer_document(file, caption="Foydalanuvchilar eksporti")
