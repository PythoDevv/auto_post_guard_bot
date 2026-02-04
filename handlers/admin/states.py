from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_group_selection = State()
    group_menu = State()
    
    # Post management
    waiting_for_post_content = State() # Photo, video, text
    waiting_for_caption = State()
    
    # Schedule management
    waiting_for_time = State()
    waiting_for_schedule_type = State()
    
    # Keyword management
    waiting_for_keyword = State()
    waiting_for_channel_id = State()

    # Admin management
    waiting_for_new_admin_id = State()
    waiting_for_remove_admin_id = State()
