from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Group, Post, ScheduleTimes, Keyword
from handlers.admin.states import AdminStates
from keyboards.inline import admin_kbs

router = Router()

@router.message(Command("admin"))
async def cmd_admin(message: types.Message, session: AsyncSession, state: FSMContext):
    # Check if user exists
    user_stmt = select(User).where(User.telegram_id == message.from_user.id)
    user_res = await session.execute(user_stmt)
    user = user_res.scalars().first()
    
    if not user:
        await message.answer("Please start the bot first with /start")
        return

    # Fetch groups owned by user
    stmt = select(Group).where(Group.owner_id == user.id)
    result = await session.execute(stmt)
    groups = result.scalars().all()
    
    if not groups:
        await message.answer("You don't have any connected groups. Add me to a group and promote me to admin first.")
        return
        
    await message.answer("Select a group to manage:", reply_markup=admin_kbs.groups_keyboard(groups))
    await state.set_state(AdminStates.waiting_for_group_selection)

@router.callback_query(F.data == "back_to_groups")
async def back_to_groups_callback(callback: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    # Re-fetch groups (logic similar to cmd_admin)
    user_stmt = select(User).where(User.telegram_id == callback.from_user.id)
    user_res = await session.execute(user_stmt)
    user = user_res.scalars().first()
    
    stmt = select(Group).where(Group.owner_id == user.id)
    result = await session.execute(stmt)
    groups = result.scalars().all()
    
    await callback.message.edit_text("Select a group to manage:", reply_markup=admin_kbs.groups_keyboard(groups))
    await state.set_state(AdminStates.waiting_for_group_selection)

@router.callback_query(F.data.startswith("group_"))
async def group_selected(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    group_id = int(callback.data.split("_")[1])
    
    # Verify ownership (optional but recommended)
    # For now assume list was filtered correctly
    
    # Store selected group in state
    await state.update_data(selected_group_id=group_id)
    
    stmt = select(Group).where(Group.id == group_id)
    res = await session.execute(stmt)
    group = res.scalars().first()
    
    if not group:
        await callback.answer("Group not found.")
        return

    await callback.message.edit_text(f"Managing Group: {group.title}", reply_markup=admin_kbs.group_main_menu_keyboard(group_id))
    await state.set_state(AdminStates.group_menu)

# --- Add Post ---
@router.callback_query(F.data.startswith("add_post_"))
async def start_add_post(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Send me the post content (Text, Photo, or Video).", reply_markup=admin_kbs.cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_post_content)

@router.message(AdminStates.waiting_for_post_content)
async def receive_post_content(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    group_id = data.get("selected_group_id")
    
    content_type = "text"
    file_id = None
    text = None
    caption = None
    
    if message.text:
        content_type = "text"
        text = message.text
    elif message.photo:
        content_type = "photo"
        file_id = message.photo[-1].file_id # Best quality
        caption = message.caption
    elif message.video:
        content_type = "video"
        file_id = message.video.file_id
        caption = message.caption
    else:
        await message.answer("Unsupported content type. Please send Text, Photo, or Video.")
        return

    post = Post(
        group_id=group_id,
        content_type=content_type,
        file_id=file_id,
        caption=caption,
        text=text
    )
    session.add(post)
    await session.commit()
    
    # Return to menu
    await message.answer("Post added successfully!")
    
    # We need to re-show the menu. 
    # Since we can't edit the user's message (this is a new message), just send a new menu.
    stmt = select(Group).where(Group.id == group_id)
    res = await session.execute(stmt)
    group = res.scalars().first()
    
    await message.answer(f"Managing Group: {group.title}", reply_markup=admin_kbs.group_main_menu_keyboard(group_id))
    await state.set_state(AdminStates.group_menu)

# --- Add Schedule ---
@router.callback_query(F.data.startswith("add_schedule_"))
async def start_add_schedule(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Send me the time for the schedule (HH:MM format, e.g. 07:00, 18:30).", reply_markup=admin_kbs.cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_time)

@router.message(AdminStates.waiting_for_time)
async def receive_schedule_time(message: types.Message, state: FSMContext, session: AsyncSession):
    import re
    time_str = message.text.strip()
    
    if not re.match(r"^\d{2}:\d{2}$", time_str):
        await message.answer("Invalid format. Please use HH:MM (e.g. 14:30).")
        return
        
    data = await state.get_data()
    group_id = data.get("selected_group_id")
    
    schedule = ScheduleTimes(
        group_id=group_id,
        time=time_str
    )
    session.add(schedule)
    await session.commit()
    
    await message.answer(f"Schedule added for {time_str}!")
    
    # Return to menu
    stmt = select(Group).where(Group.id == group_id)
    res = await session.execute(stmt)
    group = res.scalars().first()
    await message.answer(f"Managing Group: {group.title}", reply_markup=admin_kbs.group_main_menu_keyboard(group_id))
    await state.set_state(AdminStates.group_menu)

# --- Add Keyword ---
@router.callback_query(F.data.startswith("add_keyword_"))
async def start_add_keyword(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Send me the forbidden keyword.", reply_markup=admin_kbs.cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_keyword)

@router.message(AdminStates.waiting_for_keyword)
async def receive_keyword(message: types.Message, state: FSMContext, session: AsyncSession):
    keyword_text = message.text.strip()
    
    data = await state.get_data()
    group_id = data.get("selected_group_id")
    
    kw = Keyword(
        group_id=group_id,
        word=keyword_text
    )
    session.add(kw)
    await session.commit()
    
    await message.answer(f"Keyword '{keyword_text}' added!")
    
    # Return to menu
    stmt = select(Group).where(Group.id == group_id)
    res = await session.execute(stmt)
    group = res.scalars().first()
    await message.answer(f"Managing Group: {group.title}", reply_markup=admin_kbs.group_main_menu_keyboard(group_id))
    await state.set_state(AdminStates.group_menu)

# --- Cancel Action ---
@router.callback_query(F.data == "cancel_action")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Action canceled.")

# --- View Posts ---
@router.callback_query(F.data.startswith("view_posts_"))
async def view_posts(callback: types.CallbackQuery, session: AsyncSession):
    group_id = int(callback.data.split("_")[2])
    
    stmt = select(Post).where(Post.group_id == group_id)
    res = await session.execute(stmt)
    posts = res.scalars().all()
    
    if not posts:
        await callback.message.answer("No posts found.")
        return

    text = "Posts:\n"
    for p in posts:
        text += f"ID: {p.id} | Type: {p.content_type}\n"
        if p.text: text += f"Text: {p.text[:20]}...\n"
        if p.caption: text += f"Caption: {p.caption[:20]}...\n"
        text += f"/del_post_{p.id}\n\n"
    
    await callback.message.answer(text)

@router.message(F.text.startswith("/del_post_"))
async def delete_post(message: types.Message, session: AsyncSession):
    try:
        post_id = int(message.text.split("_")[2])
        stmt = select(Post).where(Post.id == post_id)
        res = await session.execute(stmt)
        post = res.scalars().first()
        
        if post:
            await session.delete(post)
            await session.commit()
            await message.answer(f"Post {post_id} deleted.")
        else:
            await message.answer("Post not found.")
    except Exception:
        await message.answer("Invalid command.")

# --- View Schedules ---
@router.callback_query(F.data.startswith("view_schedules_"))
async def view_schedules(callback: types.CallbackQuery, session: AsyncSession):
    group_id = int(callback.data.split("_")[2])
    
    stmt = select(ScheduleTimes).where(ScheduleTimes.group_id == group_id)
    res = await session.execute(stmt)
    schedules = res.scalars().all()
    
    if not schedules:
        await callback.message.answer("No schedules found.")
        return

    text = "Schedules:\n"
    for s in schedules:
        text += f"Time: {s.time} | /del_schedule_{s.id}\n"
    
    await callback.message.answer(text)

@router.message(F.text.startswith("/del_schedule_"))
async def delete_schedule(message: types.Message, session: AsyncSession):
    try:
        schedule_id = int(message.text.split("_")[2])
        stmt = select(ScheduleTimes).where(ScheduleTimes.id == schedule_id)
        res = await session.execute(stmt)
        schedule = res.scalars().first()
        
        if schedule:
            await session.delete(schedule)
            await session.commit()
            await message.answer(f"Schedule {schedule_id} deleted.")
        else:
            await message.answer("Schedule not found.")
    except Exception:
        await message.answer("Invalid command.")

# --- View Keywords ---
@router.callback_query(F.data.startswith("view_keywords_"))
async def view_keywords(callback: types.CallbackQuery, session: AsyncSession):
    group_id = int(callback.data.split("_")[2])
    
    stmt = select(Keyword).where(Keyword.group_id == group_id)
    res = await session.execute(stmt)
    keywords = res.scalars().all()
    
    if not keywords:
        await callback.message.answer("No keywords found.")
        return

    text = "Keywords:\n"
    for k in keywords:
        text += f"{k.word} | /del_keyword_{k.id}\n"
    
    await callback.message.answer(text)

@router.message(F.text.startswith("/del_keyword_"))
async def delete_keyword(message: types.Message, session: AsyncSession):
    try:
        keyword_id = int(message.text.split("_")[2])
        stmt = select(Keyword).where(Keyword.id == keyword_id)
        res = await session.execute(stmt)
        keyword = res.scalars().first()
        
        if keyword:
            await session.delete(keyword)
            await session.commit()
            await message.answer(f"Keyword {keyword_id} deleted.")
        else:
            await message.answer("Keyword not found.")
    except Exception:
        await message.answer("Invalid command.")
