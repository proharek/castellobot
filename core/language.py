import json
import os
from typing import Dict

class LanguageManager:
    def __init__(self):
        self.languages: Dict[str, Dict[str, str]] = {}
        self.default_language = "ru"
        self.supported_languages = ["ru", "ua"]
        self.load_languages()

    def load_languages(self):
        base_path = os.path.join(os.path.dirname(__file__), "..", "languages")
        for lang_code in self.supported_languages:
            path = os.path.join(base_path, f"{lang_code}.json")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.languages[lang_code] = json.load(f)
                        print(f"[LanguageManager] Загружен язык: {lang_code}")
                except Exception as e:
                    print(f"[LanguageManager] Ошибка при загрузке {lang_code}.json: {e}")
            else:
                print(f"[LanguageManager] Файл не найден: {path}")

    def get_text(self, key: str, lang: str) -> str:
        # Безопасная подстановка языка
        if lang not in self.languages:
            lang = self.default_language

        # Попытка взять перевод
        value = self.languages.get(lang, {}).get(key)

        # Если ключ найден — возвращаем
        if value:
            return value

        # Если ключ не найден — возвращаем [key]
        return f"[{key}]"
