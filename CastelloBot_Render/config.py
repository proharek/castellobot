import os
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные окружения из .env

class Config:
    # Токен бота
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

    # Префикс команд (если используете классические команды, а не app_commands)
    COMMAND_PREFIX = "/"

    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

    # Админские ID пользователей (через запятую в .env)
    @staticmethod
    def get_admin_user_ids() -> list[int]:
        raw = os.getenv("ADMIN_USER_IDS", "")
        return [int(uid.strip()) for uid in raw.split(",") if uid.strip().isdigit()]

    # Админские ID ролей (через запятую в .env)
    @staticmethod
    def get_admin_role_ids() -> list[int]:
        raw = os.getenv("ADMINS_ROLE_IDS", "")
        return [int(rid.strip()) for rid in raw.split(",") if rid.strip().isdigit()]

    # Конфигурация фонда
    FUND_PERCENTAGE = 0.5  # 50% уходит в фонд

    # Ограничение дней для отчёта
    MAX_REPORT_DAYS = 30

    # Хостинг Flask (Render)
    HOST = "0.0.0.0"
    PORT = int(os.environ.get("PORT", 8080))  # Render автоматически передаёт PORT
