from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from sqlalchemy import select
from database.engine import AsyncSessionLocal
from database.models import ScheduleTimes, Group, Post
from services.posts import send_post

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

            try:
                await send_post(bot, group.telegram_id, post_to_send)

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
