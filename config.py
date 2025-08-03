import os

class Config:
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

    DEFAULT_LANGUAGE = "ru"
    SUPPORTED_LANGUAGES = ["ru", "ua"]

    FUND_PERCENTAGE = 0.5
    MAX_CONTRACTS_DISPLAY = 25

    HOST = "0.0.0.0"
    PORT = 8080

    DEFAULT_REPORT_DAYS = 7
    MAX_REPORT_DAYS = 30

    REPORT_CLEANUP_DAYS = 7  # Автоочистка старых отчётов через /reportdays
