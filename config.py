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
    DEFAULT_REPORT_DAYS = 1    # Минимум 1 день для отчётов
    MAX_REPORT_DAYS = 30

    # Очистка старых отчётов по команде /cleanreports (дефолт 7 дней)
    REPORT_CLEANUP_DAYS = 7

    # Путь к JSON-файлу с системными контрактами
    CONTRACTS_JSON_PATH = "contracts.json"

    # Минимальный интервал между обновлениями контрактов в минутах (опционально)
    CONTRACTS_RELOAD_COOLDOWN_MINUTES = 10
