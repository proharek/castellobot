import os

class Config:
    """Настройки Discord-бота и системы"""

    # Токен Discord и ключи Supabase из переменных окружения
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

    # Языковые настройки
    DEFAULT_LANGUAGE = "ru"
    SUPPORTED_LANGUAGES = ["ru", "ua"]

    # Финансовые настройки
    FUND_PERCENTAGE = 0.5  # 50% в фонд семьи
    MAX_CONTRACTS_DISPLAY = 25

    # Сетевая часть
    COMMAND_PREFIX = "!"
    HOST = "0.0.0.0"
    PORT = 8080

    # Отчёты
    DEFAULT_REPORT_DAYS = 7
    MAX_REPORT_DAYS = 30

    # Архив и таблицы в Supabase
    ARCHIVE_ENABLED = True  # Включить функционал архива контрактов
    REPORTS_TABLE_NAME = "reports"  # Таблица для сохранённых отчётов
    CONTRACTS_TABLE_NAME = "contracts"  # Таблица для контрактов
    USERS_TABLE_NAME = "users"  # Таблица для пользователей

    # Роли и администраторы
    ADMINS_ROLE_IDS = os.getenv("ADMINS_ROLE_IDS", "")  # ID ролей админов через запятую
    ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS", "")  # ID пользователей с суперправами через запятую

    # Лимиты
    MAX_PARTICIPANTS_PER_CONTRACT = 50  # Максимальное количество участников в контракте

    @classmethod
    def get_admin_role_ids(cls) -> list[int]:
        """Вернуть список ID ролей админов из строки окружения"""
        return [int(rid.strip()) for rid in cls.ADMINS_ROLE_IDS.split(",") if rid.strip().isdigit()]

    @classmethod
    def get_admin_user_ids(cls) -> list[int]:
        """Вернуть список ID пользователей с суперправами из строки окружения"""
        return [int(uid.strip()) for uid in cls.ADMIN_USER_IDS.split(",") if uid.strip().isdigit()]

    @classmethod
    def validate(cls) -> None:
        """Проверить, что обязательные переменные окружения установлены"""
        if not cls.DISCORD_BOT_TOKEN:
            raise RuntimeError("DISCORD_BOT_TOKEN не установлен в переменных окружения")
        if not cls.SUPABASE_URL or not cls.SUPABASE_ANON_KEY:
            raise RuntimeError("SUPABASE_URL или SUPABASE_ANON_KEY не установлены")
