import os
from dotenv import load_dotenv

load_dotenv()  # Загружает переменные окружения из файла .env

class Config:
    """Настройки Discord-бота и системы"""

    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

    DEFAULT_LANGUAGE = "ru"
    SUPPORTED_LANGUAGES = ["ru", "ua"]

    FUND_PERCENTAGE = 0.5
    MAX_CONTRACTS_DISPLAY = 25

    COMMAND_PREFIX = "!"
    HOST = "0.0.0.0"
    PORT = 8080

    DEFAULT_REPORT_DAYS = 7
    MAX_REPORT_DAYS = 30

