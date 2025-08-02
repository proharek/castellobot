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
        base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "languages")
        for lang_code in self.supported_languages:
            path = os.path.join(base_path, f"{lang_code}.json")
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self.languages[lang_code] = json.load(f)
                except Exception as e:
                    print(f"[LanguageManager] Ошибка при загрузке {lang_code}.json: {e}")
            else:
                print(f"[LanguageManager] Файл не найден: {path}")

    def get_text(self, key: str, lang: str) -> str:
        # Если нет такого языка — использовать язык по умолчанию
        if lang not in self.languages:
            lang = self.default_language

        # Попробовать взять значение по ключу
        value = self.languages.get(lang, {}).get(key)
        if value is not None:
            return value

        # Попробовать взять из языка по умолчанию
        value = self.languages.get(self.default_language, {}).get(key)
        if value is not None:
            return value

        # Вернуть ключ, если ничего не найдено
        return f"[{key}]"

