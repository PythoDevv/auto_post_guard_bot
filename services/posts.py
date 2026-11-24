import json
from typing import List, Optional

from aiogram import Bot
from aiogram.types import InputMediaPhoto, InputMediaVideo, Message, MessageEntity

INPUT_MEDIA = {
    "photo": InputMediaPhoto,
    "video": InputMediaVideo,
}


def dump_entities(entities: Optional[List[MessageEntity]]) -> Optional[str]:
    if not entities:
        return None
    return json.dumps([e.model_dump(mode="json") for e in entities])


def load_entities(raw: Optional[str]) -> Optional[List[MessageEntity]]:
    if not raw:
        return None
    try:
        return [MessageEntity(**e) for e in json.loads(raw)]
    except Exception as e:
        print(f"Error parsing entities: {e}")
        return None


def _media_item(message: Message) -> Optional[dict]:
    if message.photo:
        return {"type": "photo", "file_id": message.photo[-1].file_id}  # Best quality
    if message.video:
        return {"type": "video", "file_id": message.video.file_id}
    return None


def extract_post_content(message: Message, album: Optional[List[Message]] = None) -> Optional[dict]:
    """
    Xabardan (yoki albomdan) Post maydonlarini ajratib oladi.
    Qo'llab-quvvatlanmaydigan kontent bo'lsa None qaytaradi.
    """
    content = {
        "content_type": None,
        "file_id": None,
        "caption": None,
        "text": None,
        "entities": None,
        "media": None,
    }

    if album and len(album) > 1:
        items = [_media_item(m) for m in album]
        if None in items:
            return None
        # Albomda matn odatda bitta xabarda bo'ladi (ko'pincha birinchisida)
        captioned = next((m for m in album if m.caption), None)
        content["content_type"] = "media_group"
        content["media"] = json.dumps(items)
        if captioned:
            content["caption"] = captioned.caption
            content["entities"] = dump_entities(captioned.caption_entities)
        return content

    if message.text:
        content["content_type"] = "text"
        content["text"] = message.text
        content["entities"] = dump_entities(message.entities)
        return content

    item = _media_item(message)
    if item:
        content["content_type"] = item["type"]
        content["file_id"] = item["file_id"]
        content["caption"] = message.caption
        content["entities"] = dump_entities(message.caption_entities)
        return content

    return None


def media_count(post) -> int:
    if post.content_type == "media_group" and post.media:
        return len(json.loads(post.media))
    return 1


async def send_post(bot: Bot, chat_id: int, post) -> None:
    """Postni (matn, rasm, video yoki albom) ko'rsatilgan chatga yuboradi."""
    entities = load_entities(post.entities)

    if post.content_type == "text":
        await bot.send_message(chat_id=chat_id, text=post.text, entities=entities)
    elif post.content_type == "photo":
        await bot.send_photo(chat_id=chat_id, photo=post.file_id, caption=post.caption, caption_entities=entities)
    elif post.content_type == "video":
        await bot.send_video(chat_id=chat_id, video=post.file_id, caption=post.caption, caption_entities=entities)
    elif post.content_type == "media_group":
        media = []
        for i, item in enumerate(json.loads(post.media)):
            input_cls = INPUT_MEDIA[item["type"]]
            if i == 0:
                # Birinchi elementning matni albom ostida ko'rinadi
                media.append(input_cls(media=item["file_id"], caption=post.caption, caption_entities=entities))
            else:
                media.append(input_cls(media=item["file_id"]))
        await bot.send_media_group(chat_id=chat_id, media=media)
    else:
        raise ValueError(f"Noma'lum post turi: {post.content_type}")
