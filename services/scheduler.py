import asyncio
import random
import json
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from sqlalchemy import select
from database.engine import AsyncSessionLocal
from database.models import ScheduleTimes, Group, Post

scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

async def check_scheduled_posts(bot: Bot):
    """
    Checks if there are any posts scheduled for the current minute.
    """
    tz = pytz.timezone("Asia/Tashkent")
    now_time = datetime.now(tz).strftime("%H:%M")
    
    async with AsyncSessionLocal() as session:
        # Find all groups that have a schedule at this time
        stmt = select(ScheduleTimes).where(ScheduleTimes.time == now_time)
        result = await session.execute(stmt)
        schedules = result.scalars().all()
        
        for schedule in schedules:
            group_stmt = select(Group).where(Group.id == schedule.group_id)
            group_res = await session.execute(group_stmt)
            group = group_res.scalars().first()
            
            if not group:
                continue
                
            post_to_send = None

            if schedule.post_id:
                # Specific post
                post_stmt = select(Post).where(Post.id == schedule.post_id)
                post_res = await session.execute(post_stmt)
                post_to_send = post_res.scalars().first()
            else:
                # Random/Sequential Rotation
                posts_stmt = select(Post).where(Post.group_id == group.id)
                posts_res = await session.execute(posts_stmt)
                posts = posts_res.scalars().all()
                
                if posts:
                    current_index = group.next_post_index
                    if current_index >= len(posts):
                        current_index = 0
                    
                    post_to_send = posts[current_index]
                    
                    # Update next index
                    group.next_post_index = (current_index + 1) % len(posts)
                    session.add(group)
                    await session.commit()
            
            if not post_to_send:
                continue

            # Load entities
            entities = None
            if post_to_send.entities:
                try:
                    entities = json.loads(post_to_send.entities)
                    # Aiogram 3 expects list of objects or similar?
                    # send_message(entities=...) expects list of MessageEntity
                    # We need to re-hydrate them into types.MessageEntity if aiogram strictness requires it.
                    # Actually json dicts usually work if pydantic validates, but usually passing list of dicts can work or fail.
                    # Best to re-instantiate.
                    from aiogram.types import MessageEntity
                    entities = [MessageEntity(**e) for e in entities]
                except Exception as e:
                    print(f"Error parsing entities: {e}")
                    entities = None

            try:
                if post_to_send.content_type == 'text':
                    await bot.send_message(
                        chat_id=group.telegram_id,
                        text=post_to_send.text,
                        entities=entities
                    )
                elif post_to_send.content_type == 'photo':
                    await bot.send_photo(
                        chat_id=group.telegram_id,
                        photo=post_to_send.file_id,
                        caption=post_to_send.caption,
                        caption_entities=entities
                    )
                elif post_to_send.content_type == 'video':
                    await bot.send_video(
                        chat_id=group.telegram_id,
                        video=post_to_send.file_id,
                        caption=post_to_send.caption,
                        caption_entities=entities
                    )
                # Add more types as needed
                
                # If not recurring, delete schedule
                if schedule.is_recurring == 0:
                   await session.delete(schedule)
                   await session.commit()
                   print(f"One-time schedule for group {group.title} deleted.")

            except Exception as e:
                print(f"Failed to send scheduled post to {group.title}: {e}")

def setup_scheduler(bot: Bot):
    scheduler.add_job(check_scheduled_posts, 'cron', second=0, args=[bot])
    scheduler.start()
