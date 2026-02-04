from aiogram import Router, F, types
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION, PROMOTED_TRANSITION
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Group, User

router = Router()

@router.my_chat_member()
async def on_bot_join_group(event: types.ChatMemberUpdated, session: AsyncSession):
    # Debug print
    print(f"Update received: {event.model_dump_json(exclude_none=True)}")
    
    # Check if bot was added
    new_status = event.new_chat_member.status
    if new_status not in ["member", "administrator", "creator"]:
        return # Bot left or was kicked, handled by leave handler logic if needed, but for now ignore non-joins

    # Bot joined a group or channel
    # Check if user (owner/adder) exists, if not create
    # For channels, event.from_user is who added the bot
    stmt = select(User).where(User.telegram_id == event.from_user.id)
    result = await session.execute(stmt)
    user = result.scalars().first()

    if not user:
        user = User(
            telegram_id=event.from_user.id,
            full_name=event.from_user.full_name,
            username=event.from_user.username,
            is_admin=0
        )
        session.add(user)
        # Flush to get user.id
        await session.flush()
    
    # Check if group exists
    stmt_group = select(Group).where(Group.telegram_id == event.chat.id)
    result_group = await session.execute(stmt_group)
    group = result_group.scalars().first()

    if not group:
        group = Group(
            telegram_id=event.chat.id,
            title=event.chat.title,
            is_channel=1 if event.chat.type == "channel" else 0,
            owner_id=user.id
        )
        session.add(group)
    else:
        # Update title if changed or re-joined
        group.title = event.chat.title
        # Optionally update owner if re-added by someone else? 
        # For now, keep original owner or update to current adder
        group.owner_id = user.id
    
    await session.commit()
    
    chat_type_str = "Kanal" if event.chat.type == "channel" else "Guruh"
    await event.chat.send_message(f"Meni qo'shganingiz uchun rahmat! Men {chat_type_str.lower()}ingizni boshqarishga tayyorman. Agar hali qilmagan bo'lsangiz, meni admin qiling.")

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def on_bot_leave_group(event: types.ChatMemberUpdated, session: AsyncSession):
    # Bot left or kicked
    # We can delete the group or mark as inactive.
    # Plan says: "Connect their groups". Doesn't specify deletion policy.
    # Let's just log it or maybe remove validation?
    # For now, let's keep it in DB but maybe we can add an 'active' flag later.
    # We will just print for now.
    print(f"Bot left chat: {event.chat.title} ({event.chat.id})")
    
    # Optional: Delete group from DB?
    # stmt = delete(Group).where(Group.telegram_id == event.chat.id)
    # await session.execute(stmt)
    # await session.commit()

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=PROMOTED_TRANSITION))
async def on_bot_promoted(event: types.ChatMemberUpdated, session: AsyncSession):
    # Bot promoted to admin
    # Ensure group is registered
    await on_bot_join_group(event, session) # Re-use join logic to ensure DB record
    # Maybe check specific permissions?
