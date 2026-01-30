from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def groups_keyboard(groups):
    builder = InlineKeyboardBuilder()
    for group in groups:
        builder.button(text=group.title, callback_data=f"group_{group.id}")
    builder.adjust(1)
    return builder.as_markup()

def group_main_menu_keyboard(group_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Add Post", callback_data=f"add_post_{group_id}")
    builder.button(text="Add Schedule", callback_data=f"add_schedule_{group_id}")
    builder.button(text="Add Keyword", callback_data=f"add_keyword_{group_id}")
    builder.button(text="View Posts", callback_data=f"view_posts_{group_id}")
    builder.button(text="View Schedule", callback_data=f"view_schedules_{group_id}")
    builder.button(text="View Keywords", callback_data=f"view_keywords_{group_id}")
    builder.button(text="Back to Groups", callback_data="back_to_groups")
    builder.adjust(2)
    return builder.as_markup()

def cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Cancel", callback_data="cancel_action")
    return builder.as_markup()
