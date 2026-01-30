from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Keyword, Group as DBGroup

class SpamFilterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        # Skip if message is from private chat
        if event.chat.type == "private":
            return await handler(event, data)

        session: AsyncSession = data.get("session")
        if not session:
            # Should not happen if DbSessionMiddleware is registered before
            return await handler(event, data)

        # Check if group is registered and has keywords
        # Optimization: We might want to cache this, but for now we query.
        # We need the group from DB.
        
        # NOTE: Group registration logic should probably happen in another middleware or handler. 
        # But assuming the group is known or we look it up by telegram_id.
        
        stmt = select(DBGroup).where(DBGroup.telegram_id == event.chat.id)
        result = await session.execute(stmt)
        group = result.scalars().first()

        if not group:
            return await handler(event, data)

        # Fetch keywords for this group
        # Ideally we join or lazy load on the group object if we had it, but session usage intricacies...
        # Let's just fetch keywords directly.
        stmt_kw = select(Keyword.word).where(Keyword.group_id == group.id)
        result_kw = await session.execute(stmt_kw)
        keywords = result_kw.scalars().all()

        if not keywords:
            return await handler(event, data)

        text = event.text or event.caption or ""
        if not text:
            return await handler(event, data)
            
        text_lower = text.lower()
        
        for kw in keywords:
            if kw.lower() in text_lower:
                # Spam detected
                try:
                    await event.delete()
                    if group.owner_id:
                        # Fetch owner telegram_id
                        # group.owner might not be loaded if we didn't eager load.
                        # But group.owner_id is an integer (FK). 
                        # We need the User object to get telegram_id.
                        from database.models import User
                        stmt_user = select(User).where(User.id == group.owner_id)
                        res_user = await session.execute(stmt_user)
                        owner = res_user.scalars().first()
                        
                        if owner:
                            await event.bot.forward_message(
                                chat_id=owner.telegram_id,
                                from_chat_id=event.chat.id,
                                message_id=event.message_id
                            )
                            # Maybe send a notification too?
                            await event.bot.send_message(
                                chat_id=owner.telegram_id,
                                text=f"Spam detected in group {group.title} and deleted.\nKeyword: {kw}"
                            )
                except Exception as e:
                    print(f"Error in spam filter: {e}")
                
                # Stop propagation
                return

        return await handler(event, data)
