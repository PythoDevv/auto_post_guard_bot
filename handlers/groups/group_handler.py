from aiogram import Router, F
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_NOT_MEMBER, MEMBER, ADMINISTRATOR
from aiogram.types import Message, ChatMemberUpdated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Group, User

router = Router()

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> MEMBER))
@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> ADMINISTRATOR))
@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER >> ADMINISTRATOR))
async def on_bot_added_or_promoted(event: ChatMemberUpdated, session: AsyncSession):
    # Check if bot is the one updated (it should be for my_chat_member, but always good to check)
    if event.new_chat_member.user.id != event.bot.id:
        return

    # Bot was added or promoted
    await event.bot.send_message(
        chat_id=event.chat.id, 
        text="Hello! I am Auto Post Guard Bot.\nTo set me up, an admin must use /register."
    )

@router.message(Command("register"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_register_group(message: Message, session: AsyncSession):
    # Check if user is admin in chat
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    
    # Check status by string to avoid import complexity
    if member.status not in ("administrator", "creator"):
        await message.reply("You must be an admin to register this group.")
        return

    # Check if user is registered in bot
    stmt = select(User).where(User.telegram_id == message.from_user.id)
    res = await session.execute(stmt)
    user = res.scalars().first()
    
    if not user:
        await message.reply("Please start me in private chat first: /start")
        return

    # Check if group already exists
    stmt_group = select(Group).where(Group.telegram_id == message.chat.id)
    res_group = await session.execute(stmt_group)
    group = res_group.scalars().first()

    if group:
        if group.owner_id != user.id:
            await message.reply("Group is already registered by another user.")
        else:
            await message.reply("Group is already registered to you.")
        return

    # Register group
    new_group = Group(
        telegram_id=message.chat.id,
        title=message.chat.title,
        owner_id=user.id
    )
    session.add(new_group)
    await session.commit()
    await message.reply("Group registered successfully! You can now configure it in my private chat.")
