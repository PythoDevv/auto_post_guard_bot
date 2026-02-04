from aiogram import Router, types
from aiogram.filters import CommandStart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, session: AsyncSession):
    # Check if user exists
    stmt = select(User).where(User.telegram_id == message.from_user.id)
    result = await session.execute(stmt)
    user = result.scalars().first()

    if not user:
        user = User(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
            is_admin=0 
        )
        session.add(user)
        # We need to commit here to save the user
        await session.commit()
        await message.answer(f"Xush kelibsiz, {message.from_user.full_name}! Siz ro'yxatdan o'tdingiz.")
    else:
        # Update info if changed
        if user.full_name != message.from_user.full_name or user.username != message.from_user.username:
             user.full_name = message.from_user.full_name
             user.username = message.from_user.username
             await session.commit()
        
        await message.answer("Qaytganingizdan xursandmiz!")
