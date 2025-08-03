import os

class Config:
    # Токен бота из переменных окружения (.env или Render settings)
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

    # Язык по умолчанию и поддерживаемые языки
    DEFAULT_LANGUAGE = "ru"
    SUPPORTED_LANGUAGES = ["ru", "ua"]

    # Процент от контракта, уходящий в фонд
    FUND_PERCENTAGE = 0.5

    # Максимум контрактов в select-меню
    MAX_CONTRACTS_DISPLAY = 25

    # Настройки Flask (для Render / UptimeRobot)
    HOST = "0.0.0.0"
    PORT = 8080

    # Настройки отчёта за дни
    DEFAULT_REPORT_DAYS = 7
    MAX_REPORT_DAYS = 30

    # Сколько дней хранить отчёты (используется при /reportdays)
    REPORT_CLEANUP_DAYS = 7
