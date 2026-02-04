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
        await message.answer("Iltimos, avval botni /start buyrug'i bilan ishga tushiring")
        return

    # Fetch groups owned by user
    stmt = select(Group).where(Group.owner_id == user.id)
    result = await session.execute(stmt)
    groups = result.scalars().all()
    
    # If no groups, still show the user a message but maybe with a help button or just stats
    group_count = len([g for g in groups if g.is_channel == 0])
    channel_count = len([g for g in groups if g.is_channel == 1])
    
    msg_text = f"Sizda {group_count} ta guruh va {channel_count} ta kanal mavjud."
    
    if not groups:
        msg_text += "\n\nGuruh yoki kanal qo'shish uchun meni unga qo'shing va admin qiling."
        
    await message.answer(msg_text, reply_markup=admin_kbs.groups_keyboard(groups, user.telegram_id))
    
    # We always set state to allow navigation if they have buttons (like Admin Management)
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
    
    await callback.message.edit_text("Boshqarish uchun guruhni tanlang:", reply_markup=admin_kbs.groups_keyboard(groups))
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
        await callback.answer("Guruh topilmadi.")
        return

    await callback.message.edit_text(f"Guruhni boshqarish: {group.title}", reply_markup=admin_kbs.group_main_menu_keyboard(group_id))
    await state.set_state(AdminStates.group_menu)

# --- Add Post ---
@router.callback_query(F.data.startswith("add_post_"))
async def start_add_post(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Post mazmunini yuboring (Matn, Rasm yoki Video).", reply_markup=admin_kbs.cancel_keyboard())
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
        await message.answer("Qollab-quvvatlanmagan kontent turi. Iltimos, Matn, Rasm yoki Video yuboring.")
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
    await message.answer("Post muvaffaqiyatli qo'shildi!")
    
    # We need to re-show the menu. 
    # Since we can't edit the user's message (this is a new message), just send a new menu.
    stmt = select(Group).where(Group.id == group_id)
    res = await session.execute(stmt)
    group = res.scalars().first()
    
    await message.answer(f"Guruhni boshqarish: {group.title}", reply_markup=admin_kbs.group_main_menu_keyboard(group_id))
    await state.set_state(AdminStates.group_menu)

# --- Add Schedule ---
@router.callback_query(F.data.startswith("add_schedule_"))
async def start_add_schedule(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Jadval vaqtini yuboring (HH:MM formatida, masalan 07:00, 18:30).", reply_markup=admin_kbs.cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_time)

@router.message(AdminStates.waiting_for_time)
async def receive_schedule_time(message: types.Message, state: FSMContext, session: AsyncSession):
    import re
    time_str = message.text.strip()
    
    if not re.match(r"^\d{2}:\d{2}$", time_str):
        await message.answer("Noto'g'ri format. Iltimos HH:MM ishlating (masalan 14:30).")
        return
        
    data = await state.get_data()
    group_id = data.get("selected_group_id")
    
    schedule = ScheduleTimes(
        group_id=group_id,
        time=time_str
    )
    session.add(schedule)
    await session.commit()
    
    await message.answer(f"{time_str} ga jadval qo'shildi!")
    
    # Return to menu
    stmt = select(Group).where(Group.id == group_id)
    res = await session.execute(stmt)
    group = res.scalars().first()
    await message.answer(f"Guruhni boshqarish: {group.title}", reply_markup=admin_kbs.group_main_menu_keyboard(group_id))
    await state.set_state(AdminStates.group_menu)

# --- Add Keyword ---
@router.callback_query(F.data.startswith("add_keyword_"))
async def start_add_keyword(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Taqiqlangan so'zni yuboring.", reply_markup=admin_kbs.cancel_keyboard())
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
    
    await message.answer(f"'{keyword_text}' so'zi qo'shildi!")
    
    # Return to menu
    stmt = select(Group).where(Group.id == group_id)
    res = await session.execute(stmt)
    group = res.scalars().first()
    await message.answer(f"Guruhni boshqarish: {group.title}", reply_markup=admin_kbs.group_main_menu_keyboard(group_id))
    await state.set_state(AdminStates.group_menu)

# --- Cancel Action ---
@router.callback_query(F.data == "cancel_action")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Amal bekor qilindi.")

# --- View Posts ---
@router.callback_query(F.data.startswith("view_posts_"))
async def view_posts(callback: types.CallbackQuery, session: AsyncSession):
    group_id = int(callback.data.split("_")[2])
    
    stmt = select(Post).where(Post.group_id == group_id)
    res = await session.execute(stmt)
    posts = res.scalars().all()
    
    if not posts:
        await callback.message.answer("Postlar topilmadi.")
        return

    text = "Postlar:\n"
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
            await message.answer(f"Post {post_id} o'chirildi.")
        else:
            await message.answer("Post topilmadi.")
    except Exception:
        await message.answer("Noto'g'ri buyruq.")

# --- View Schedules ---
@router.callback_query(F.data.startswith("view_schedules_"))
async def view_schedules(callback: types.CallbackQuery, session: AsyncSession):
    group_id = int(callback.data.split("_")[2])
    
    stmt = select(ScheduleTimes).where(ScheduleTimes.group_id == group_id)
    res = await session.execute(stmt)
    schedules = res.scalars().all()
    
    if not schedules:
        await callback.message.answer("Jadvallar topilmadi.")
        return

    text = "Jadvallar:\n"
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
            await message.answer(f"Jadval {schedule_id} o'chirildi.")
        else:
            await message.answer("Jadval topilmadi.")
    except Exception:
        await message.answer("Noto'g'ri buyruq.")

# --- View Keywords ---
@router.callback_query(F.data.startswith("view_keywords_"))
async def view_keywords(callback: types.CallbackQuery, session: AsyncSession):
    group_id = int(callback.data.split("_")[2])
    
    stmt = select(Keyword).where(Keyword.group_id == group_id)
    res = await session.execute(stmt)
    keywords = res.scalars().all()
    
    if not keywords:
        await callback.message.answer("Kalit so'zlar topilmadi.")
        return

    text = "Kalit so'zlar:\n"
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
            await message.answer(f"Kalit so'z {keyword_id} o'chirildi.")
        else:
            await message.answer("Kalit so'z topilmadi.")
    except Exception:
        await message.answer("Noto'g'ri buyruq.")
# --- Manual Channel Addition ---
@router.callback_query(F.data == "manual_add_channel")
async def start_manual_add_channel(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Kanalni qo'shish uchun uning Username (masalan @kanal_nomi) yoki ID sini (-100...) yuboring.\n"
        "Muhim: Bot avval kanalga admin qilingan bo'lishi kerak!",
        reply_markup=admin_kbs.cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_channel_id)

@router.message(AdminStates.waiting_for_channel_id)
async def process_manual_channel(message: types.Message, state: FSMContext, session: AsyncSession):
    input_data = message.text.strip()
    
    # Try to resolve chat
    try:
        chat = await message.bot.get_chat(input_data)
    except Exception:
        await message.answer("Kanal topilmadi yoki bot u yerda yo'q. Iltimos tekshirib qaytadan yuboring.")
        return

    if chat.type != "channel" and chat.type != "supergroup":
         await message.answer("Bu kanal yoki guruh emas.")
         return
         
    # Check if bot is admin there (optional, but good practice)
    # get_chat doesn't explicitly return 'is_admin' for the bot, but we can try get_chat_member
    try:
        member = await message.bot.get_chat_member(chat.id, message.bot.id)
        if member.status not in ["administrator", "creator"]:
             await message.answer("Bot kanalga admin qilinmagan. Iltimos avval botni admin qiling.")
             return
    except Exception:
         # If we can't get member, we are probably not in the chat
         await message.answer("Bot kanalga qo'shilmagan. Iltimos avval botni qo'shing.")
         return

    # User logic
    user_stmt = select(User).where(User.telegram_id == message.from_user.id)
    user_res = await session.execute(user_stmt)
    user = user_res.scalars().first()
    
    if not user:
        # Create user if missing (should be there if they used /start or /admin)
        user = User(telegram_id=message.from_user.id, full_name=message.from_user.full_name)
        session.add(user)
        await session.flush()

    # Create/Update Group/Channel
    stmt_group = select(Group).where(Group.telegram_id == chat.id)
    result_group = await session.execute(stmt_group)
    group = result_group.scalars().first()

    is_channel = 1 if chat.type == "channel" else 0

    if not group:
        group = Group(
            telegram_id=chat.id,
            title=chat.title,
            is_channel=is_channel,
            owner_id=user.id
        )
        session.add(group)
        await message.answer(f"{chat.title} muvaffaqiyatli qo'shildi!")
    else:
        # Update owner to current user? Or just say it exists?
        # Let's update owner to be safe if they are claiming it
        group.owner_id = user.id
        group.title = chat.title
        group.is_channel = is_channel
        await message.answer(f"{chat.title} ma'lumotlari yangilandi va sizga biriktirildi.")
        
    await session.commit()
    await state.clear()
    
    # Show main menu
    await cmd_admin(message, session, state)
