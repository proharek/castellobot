import os

class Config:
    """Настройки Discord-бота и системы"""

    # Токен Discord-бота из переменной окружения
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

    # Языки
    DEFAULT_LANGUAGE = "ru"
    SUPPORTED_LANGUAGES = ["ru", "ua"]

    # Финансовые параметры
    FUND_PERCENTAGE = 0.5  # 50% в фонд
    MAX_CONTRACTS_DISPLAY = 25  # максимум отображаемых контрактов

    # Команды
    COMMAND_PREFIX = "!"

    # Хостинг Flask (Render)
    HOST = "0.0.0.0"
    PORT = int(os.environ.get("PORT", 8080))  # Render задаёт PORT, иначе 8080

    # Отчёты
    DEFAULT_REPORT_DAYS = 7
    MAX_REPORT_DAYS = 30
