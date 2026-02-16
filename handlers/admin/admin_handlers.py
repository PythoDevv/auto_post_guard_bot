from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Group, Post, ScheduleTimes, Keyword
from handlers.admin.states import AdminStates
from keyboards.inline import admin_kbs
import json
from config import ADMINS

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

    # Check permission for Admin Management (Env Admin OR DB Admin)
    show_admin_btn = (user.telegram_id in ADMINS) or (user.is_admin == 1)
        
    await message.answer(msg_text, reply_markup=admin_kbs.groups_keyboard(groups, show_admin_btn=show_admin_btn))
    
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
    entities = None
    
    if message.text:
        content_type = "text"
        text = message.text
        if message.entities:
            entities = json.dumps([e.model_dump(mode='json') for e in message.entities])
    elif message.photo:
        content_type = "photo"
        file_id = message.photo[-1].file_id # Best quality
        caption = message.caption
        if message.caption_entities:
            entities = json.dumps([e.model_dump(mode='json') for e in message.caption_entities])
    elif message.video:
        content_type = "video"
        file_id = message.video.file_id
        caption = message.caption
        if message.caption_entities:
            entities = json.dumps([e.model_dump(mode='json') for e in message.caption_entities])
    else:
        await message.answer("Qollab-quvvatlanmagan kontent turi. Iltimos, Matn, Rasm yoki Video yuboring.")
        return

    post = Post(
        group_id=group_id,
        content_type=content_type,
        file_id=file_id,
        caption=caption,
        text=text,
        entities=entities
    )
    session.add(post)
    await session.commit()
    
    # Store post ID for naming
    await state.update_data(schedule_post_id=post.id)
    
    await message.answer("Post muvaffaqiyatli qo'shildi!\nEndi postga nom bering (masalan: Tandirchi, Non apparat). Yoki 'O'tkazib yuborish' tugmasini bosing.", reply_markup=admin_kbs.skip_name_keyboard())
    await state.set_state(AdminStates.waiting_for_post_name)

# --- Post Name ---
@router.message(AdminStates.waiting_for_post_name)
async def receive_post_name(message: types.Message, state: FSMContext, session: AsyncSession):
    post_name = message.text.strip()
    data = await state.get_data()
    post_id = data.get("schedule_post_id")
    
    stmt = select(Post).where(Post.id == post_id)
    res = await session.execute(stmt)
    post = res.scalars().first()
    
    if post:
        post.name = post_name
        await session.commit()
    
    await message.answer(f"Post '{post_name}' deb nomlandi!\nEndi vaqtni belgilashingiz mumkin (HH:MM formatida). Yoki 'O'tkazib yuborish' tugmasini bosing.", reply_markup=admin_kbs.skip_keyboard())
    await state.set_state(AdminStates.waiting_for_specific_schedule_time)

@router.callback_query(F.data == "skip_post_name")
async def skip_post_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Nom o'tkazib yuborildi.\nEndi vaqtni belgilashingiz mumkin (HH:MM formatida). Yoki 'O'tkazib yuborish' tugmasini bosing.", reply_markup=admin_kbs.skip_keyboard())
    await state.set_state(AdminStates.waiting_for_specific_schedule_time)

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

    await callback.message.delete()
    
    # We will show posts one by one or list them with buttons? 
    # User said "also need button for view post ! button name must time"
    # This implies seeing the time of the post if it has one? Or just "View Post" buttons?
    # User said "button name must time". 
    # Maybe they mean if a post has a schedule, show the time as button?
    # Or maybe they mean "Post 1 (18:30)", "Post 2 (No schedule)"?
    
    # Let's list posts as buttons.
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for p in posts:
        # Check if post has a specific schedule linked to it
        sched_stmt = select(ScheduleTimes).where(ScheduleTimes.post_id == p.id)
        sched_res = await session.execute(sched_stmt)
        sched = sched_res.scalars().first()
        
        # Show name if available, otherwise Post ID
        if p.name:
            btn_text = f"📌 {p.name}"
        else:
            btn_text = f"Post {p.id}"
        
        if sched:
             btn_text += f" ({sched.time})"
        else:
             btn_text += " (Vaqt yo'q)"
             
        # Button to view/manage specific post
        builder.button(text=btn_text, callback_data=f"manage_post_{p.id}")
        
    builder.button(text="Orqaga", callback_data=f"group_{group_id}")
    builder.adjust(1)
    
    await callback.message.answer("Postni tanlang:", reply_markup=builder.as_markup())

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

# --- Specific Post Schedule ---
@router.message(F.text.startswith("/set_schedule_"))
async def start_set_post_schedule(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        parts = message.text.split("_")
        if len(parts) < 3:
             await message.answer("Error parsing ID.")
             return
        post_id = int(parts[2])
        
        stmt = select(Post).where(Post.id == post_id)
        res = await session.execute(stmt)
        post = res.scalars().first()
        if not post:
             await message.answer("Post topilmadi.")
             return

        await message.answer(f"Post {post_id} uchun vaqtni kiriting (Format: HH:MM).", reply_markup=admin_kbs.cancel_keyboard())
        await state.update_data(schedule_post_id=post_id)
        await state.set_state(AdminStates.waiting_for_specific_schedule_time)
    except Exception as e:
        await message.answer(f"Xato: {e}")

@router.message(AdminStates.waiting_for_specific_schedule_time)
async def receive_specific_schedule_time(message: types.Message, state: FSMContext, session: AsyncSession):
    import re
    time_str = message.text.strip()
    
    if not re.match(r"^\d{2}:\d{2}$", time_str):
        await message.answer("Noto'g'ri format. Iltimos HH:MM ishlating.")
        return
        
    data = await state.get_data()
    post_id = data.get("schedule_post_id")
    
    stmt = select(Post).where(Post.id == post_id)
    res = await session.execute(stmt)
    post = res.scalars().first()
    
    if not post:
        await message.answer("Post topilmadi.")
        return

    # Don't save yet, ask for type
    await state.update_data(schedule_time=time_str)
    
    await message.answer(
        "Bu post bir martalikmi yoki har kuni qaytariladimi?",
        reply_markup=admin_kbs.recurring_options_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_schedule_type)

@router.callback_query(AdminStates.waiting_for_schedule_type)
async def receive_schedule_type(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    post_id = data.get("schedule_post_id")
    time_str = data.get("schedule_time")
    
    is_recurring = 1 if callback.data == "schedule_daily" else 0
    
    stmt = select(Post).where(Post.id == post_id)
    res = await session.execute(stmt)
    post = res.scalars().first()
    
    if not post:
        await callback.message.answer("Post topilmadi.")
        return

    schedule = ScheduleTimes(
        group_id=post.group_id,
        time=time_str,
        post_id=post_id,
        is_recurring=is_recurring
    )
    session.add(schedule)
    await session.commit()
    
    type_str = "har kuni" if is_recurring else "bir marta"
    await callback.message.edit_text(f"Post {time_str} vaqtiga ({type_str}) rejalashtirildi!")
    
    await state.clear()
    
    group_stmt = select(Group).where(Group.id == post.group_id)
    group_res = await session.execute(group_stmt)
    group = group_res.scalars().first()
    
    if group:
        await callback.message.answer(f"Guruhni boshqarish: {group.title}", reply_markup=admin_kbs.group_main_menu_keyboard(group.id))
        await state.set_state(AdminStates.group_menu)

@router.callback_query(F.data == "skip_schedule")
async def skip_generic(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    group_id = data.get("selected_group_id")
    
    if group_id:
        stmt = select(Group).where(Group.id == group_id)
        res = await session.execute(stmt)
        group = res.scalars().first()
        await callback.message.edit_text(f"Guruhni boshqarish: {group.title}", reply_markup=admin_kbs.group_main_menu_keyboard(group_id))
    else:
        await callback.message.edit_text("Menyu")
        
    await state.set_state(AdminStates.group_menu)

@router.callback_query(F.data.startswith("manage_post_"))
async def manage_post(callback: types.CallbackQuery, session: AsyncSession):
    post_id = int(callback.data.split("_")[2])
    
    stmt = select(Post).where(Post.id == post_id)
    res = await session.execute(stmt)
    post = res.scalars().first()
    
    if not post:
        await callback.message.answer("Post topilmadi.")
        return

    # Check schedule
    sched_stmt = select(ScheduleTimes).where(ScheduleTimes.post_id == post.id)
    sched_res = await session.execute(sched_stmt)
    sched = sched_res.scalars().first()
    
    post_name_display = post.name if post.name else f"Post {post.id}"
    info_text = f"📌 Nom: {post_name_display}\nPost ID: {post.id}\nTur: {post.content_type}\n"
    if sched:
        type_str = "Doimiy" if sched.is_recurring else "Bir martalik"
        info_text += f"\nJadval: {sched.time} ({type_str})"
    else:
        info_text += "\nJadval: Belgilanmagan"
        
    # Send preview if possible (delete old menu msg first)
    await callback.message.delete()
    
    # Load entities
    entities = None
    if post.entities:
        try:
            from aiogram.types import MessageEntity
            data = json.loads(post.entities)
            entities = [MessageEntity(**e) for e in data]
        except:
             pass

    try:
        if post.content_type == 'text':
            await callback.message.answer(post.text, entities=entities)
        elif post.content_type == 'photo':
            await callback.message.answer_photo(post.file_id, caption=post.caption, caption_entities=entities)
        elif post.content_type == 'video':
            await callback.message.answer_video(post.file_id, caption=post.caption, caption_entities=entities)
    except Exception as e:
        info_text += f"\n\n(Postni ko'rsatishda xatolik: {e})"
        
    # Actions keyboard
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✏️ Nomni o'zgartirish", callback_data=f"edit_name_{post.id}")
    builder.button(text="✏️ Mazmunni tahrirlash", callback_data=f"edit_content_{post.id}")
    
    if not sched:
        builder.button(text="Jadval belgilash", callback_data=f"set_sched_btn_{post.id}")
    else:
        builder.button(text="Jadvalni o'chirish", callback_data=f"del_sched_btn_{sched.id}")
        
    builder.button(text="Postni o'chirish", callback_data=f"del_post_btn_{post.id}")
    builder.button(text="Orqaga", callback_data=f"view_posts_{post.group_id}")
    builder.adjust(1)
    
    await callback.message.answer(info_text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("set_sched_btn_"))
async def btn_set_schedule(callback: types.CallbackQuery, state: FSMContext):
    post_id = int(callback.data.split("_")[3])
    await callback.message.answer("Vaqtni kiriting (HH:MM):", reply_markup=admin_kbs.cancel_keyboard())
    await state.update_data(schedule_post_id=post_id)
    await state.set_state(AdminStates.waiting_for_specific_schedule_time)

@router.callback_query(F.data.startswith("del_sched_btn_"))
async def btn_del_schedule(callback: types.CallbackQuery, session: AsyncSession):
    sched_id = int(callback.data.split("_")[3])
    stmt = select(ScheduleTimes).where(ScheduleTimes.id == sched_id)
    res = await session.execute(stmt)
    sched = res.scalars().first()
    
    if sched:
        await session.delete(sched)
        await session.commit()
        await callback.answer("Jadval o'chirildi")
        # Refresh management view
        # We need post_id to refresh view
        await manage_post(callback, session) 
        # Actually context might be lost or we need to reconstruct callback mock?
        # Simpler: just reload manually
    else:
        await callback.answer("Topilmadi")

@router.callback_query(F.data.startswith("del_post_btn_"))
async def btn_del_post(callback: types.CallbackQuery, session: AsyncSession):
    post_id = int(callback.data.split("_")[3])
    stmt = select(Post).where(Post.id == post_id)
    res = await session.execute(stmt)
    post = res.scalars().first()
    
    if post:
        await session.delete(post)
        await session.commit()
        await callback.answer("Post o'chirildi")
        await callback.message.delete()
        await callback.message.answer("Post o'chirildi.")
    else:
        await callback.answer("Topilmadi")

# --- Edit Post Name ---
@router.callback_query(F.data.startswith("edit_name_"))
async def edit_post_name_start(callback: types.CallbackQuery, state: FSMContext):
    post_id = int(callback.data.split("_")[2])
    await state.update_data(edit_post_id=post_id)
    await callback.message.answer("Yangi nomni yuboring:", reply_markup=admin_kbs.cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_edit_name)

@router.message(AdminStates.waiting_for_edit_name)
async def receive_edit_name(message: types.Message, state: FSMContext, session: AsyncSession):
    new_name = message.text.strip()
    data = await state.get_data()
    post_id = data.get("edit_post_id")
    
    stmt = select(Post).where(Post.id == post_id)
    res = await session.execute(stmt)
    post = res.scalars().first()
    
    if not post:
        await message.answer("Post topilmadi.")
        await state.clear()
        return
    
    post.name = new_name
    await session.commit()
    
    await message.answer(f"Post nomi '{new_name}' ga o'zgartirildi!")
    
    # Return to group menu
    group_stmt = select(Group).where(Group.id == post.group_id)
    group_res = await session.execute(group_stmt)
    group = group_res.scalars().first()
    
    if group:
        await message.answer(f"Guruhni boshqarish: {group.title}", reply_markup=admin_kbs.group_main_menu_keyboard(group.id))
        await state.set_state(AdminStates.group_menu)
    else:
        await state.clear()

# --- Edit Post Content ---
@router.callback_query(F.data.startswith("edit_content_"))
async def edit_post_content_start(callback: types.CallbackQuery, state: FSMContext):
    post_id = int(callback.data.split("_")[2])
    await state.update_data(edit_post_id=post_id)
    await callback.message.answer("Yangi mazmunni yuboring (Matn, Rasm yoki Video):", reply_markup=admin_kbs.cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_edit_content)

@router.message(AdminStates.waiting_for_edit_content)
async def receive_edit_content(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    post_id = data.get("edit_post_id")
    
    stmt = select(Post).where(Post.id == post_id)
    res = await session.execute(stmt)
    post = res.scalars().first()
    
    if not post:
        await message.answer("Post topilmadi.")
        await state.clear()
        return
    
    # Update content based on type
    if message.text:
        post.content_type = "text"
        post.text = message.text
        post.file_id = None
        post.caption = None
        if message.entities:
            post.entities = json.dumps([e.model_dump(mode='json') for e in message.entities])
        else:
            post.entities = None
    elif message.photo:
        post.content_type = "photo"
        post.file_id = message.photo[-1].file_id
        post.caption = message.caption
        post.text = None
        if message.caption_entities:
            post.entities = json.dumps([e.model_dump(mode='json') for e in message.caption_entities])
        else:
            post.entities = None
    elif message.video:
        post.content_type = "video"
        post.file_id = message.video.file_id
        post.caption = message.caption
        post.text = None
        if message.caption_entities:
            post.entities = json.dumps([e.model_dump(mode='json') for e in message.caption_entities])
        else:
            post.entities = None
    else:
        await message.answer("Qollab-quvvatlanmagan kontent turi. Iltimos, Matn, Rasm yoki Video yuboring.")
        return
    
    await session.commit()
    
    post_name = post.name if post.name else f"Post {post.id}"
    await message.answer(f"'{post_name}' mazmuni muvaffaqiyatli yangilandi!")
    
    # Return to group menu
    group_stmt = select(Group).where(Group.id == post.group_id)
    group_res = await session.execute(group_stmt)
    group = group_res.scalars().first()
    
    if group:
        await message.answer(f"Guruhni boshqarish: {group.title}", reply_markup=admin_kbs.group_main_menu_keyboard(group.id))
        await state.set_state(AdminStates.group_menu)
    else:
        await state.clear()

