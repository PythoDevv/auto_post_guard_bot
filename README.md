# Auto Post Guard Bot

A Telegram bot for managing groups, scheduling posts, and specialized admin management.

## Setup

1.  **Clone the repository** (if not already done).
2.  **Create a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Environment Variables**:
    Create a `.env` file in the root directory with the following variables:

    ```env
    BOT_TOKEN=your_bot_token_here
    ADMINS=123456789,987654321
    
    # Database Configuration (PostgreSQL)
    DB_USER=postgres
    DB_PASS=postgres
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=auto_post_guard_bot
    ```

    *Note: `ADMINS` is a comma-separated list of Telegram IDs for Superadmins who can manage other admins.*

2.  **Database**:
    Ensure you have a PostgreSQL database running and created with the name specified in `DB_NAME`.
    
    Example creating DB in psql:
    ```sql
    CREATE DATABASE auto_post_guard_bot;
    ```

## Running the Bot

Run the bot with:
```bash
python3 bot.py
```

## Features

- **Group Management**: Connect groups, manage settings.
- **Post Scheduling**: Schedule posts for groups.
- **Admin Management**: 
    - Use `/admin` to access the panel.
    - Superadmins (in `.env`) can Add/Remove/List other admins via the "Admin Management" menu.
