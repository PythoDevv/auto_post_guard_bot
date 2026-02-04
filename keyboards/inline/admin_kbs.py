from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMINS

def groups_keyboard(groups, show_admin_btn=False):
    builder = InlineKeyboardBuilder()
    for group in groups:
        builder.button(text=group.title, callback_data=f"group_{group.id}")
    
    # Add Admin Management button if permission granted
    if show_admin_btn:
         builder.button(text="Admin boshqaruvi", callback_data="admin_management")
         
    builder.button(text="➕ Kanal/Guruh qo'shish", callback_data="manual_add_channel")

    builder.adjust(1)
    return builder.as_markup()

def skip_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="O'tkazib yuborish", callback_data="skip_schedule")
    return builder.as_markup()

def group_main_menu_keyboard(group_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Post qo'shish", callback_data=f"add_post_{group_id}")
    # builder.button(text="Jadval qo'shish", callback_data=f"add_schedule_{group_id}") # Removed per user request
    # builder.button(text="Kalit so'z qo'shish", callback_data=f"add_keyword_{group_id}") # Removed
    builder.button(text="Postlarni ko'rish", callback_data=f"view_posts_{group_id}")
    builder.button(text="Jadvalni ko'rish", callback_data=f"view_schedules_{group_id}")
    # builder.button(text="Kalit so'zlarni ko'rish", callback_data=f"view_keywords_{group_id}") # Removed
    builder.button(text="Guruhlarga qaytish", callback_data="back_to_groups")
    builder.adjust(2)
    return builder.as_markup()

def recurring_options_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Bir martalik", callback_data="schedule_once")
    builder.button(text="Doimiy (Har kuni)", callback_data="schedule_daily")
    return builder.as_markup()

def cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Bekor qilish", callback_data="cancel_action")
    return builder.as_markup()

def admin_management_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Adminlar ro'yxati", callback_data="list_admins")
    builder.button(text="Admin qo'shish", callback_data="add_admin")
    builder.button(text="Admin o'chirish", callback_data="remove_admin")
    # Back to home/main admin menu if we have one, or just close
    # For now no 'back' to main menu since main menu is context sensitive (groups)
    return builder.as_markup()

def back_to_admin_management():
    builder = InlineKeyboardBuilder()
    builder.button(text="Orqaga", callback_data="admin_management")
    return builder.as_markup()
