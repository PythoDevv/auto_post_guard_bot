from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_group_selection = State()
    group_menu = State()
    
    # Post management
    waiting_for_post_content = State() # Photo, video, text
    waiting_for_caption = State()
    
    # Schedule management
    waiting_for_time = State()
    
    # Keyword management
    waiting_for_keyword = State()
