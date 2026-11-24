import asyncio
from typing import Any, Awaitable, Callable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class AlbumMiddleware(BaseMiddleware):
    """
    Telegram albomni (media group) botga har bir rasm/video uchun alohida xabar qilib yuboradi.
    Bu middleware ularni yig'ib, handlerni faqat bir marta chaqiradi va
    `album` argumentida barcha xabarlarni (message_id bo'yicha tartiblangan) beradi.
    """

    def __init__(self, latency: float = 1.0):
        # Oxirgi xabardan keyin shuncha sekund yangi xabar kelmasa, albom to'liq deb hisoblanadi
        self.latency = latency
        self.albums: Dict[str, List[Message]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.media_group_id:
            return await handler(event, data)

        group_id = event.media_group_id
        if group_id in self.albums:
            # Albomning keyingi qismi: faqat ro'yxatga qo'shamiz, handler chaqirilmaydi
            self.albums[group_id].append(event)
            return None

        self.albums[group_id] = [event]
        count = 0
        while count != len(self.albums[group_id]):
            count = len(self.albums[group_id])
            await asyncio.sleep(self.latency)

        album = sorted(self.albums.pop(group_id), key=lambda m: m.message_id)
        data["album"] = album
        return await handler(event, data)
