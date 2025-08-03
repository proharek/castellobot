import json
import os

class LanguageManager:
    def __init__(self, lang_folder: str = "lang"):
        self.lang_folder = lang_folder
        self.texts = {}
        self.load_languages()

    def load_languages(self):
        for lang_code in ["ru", "ua"]:
            path = os.path.join(self.lang_folder, f"{lang_code}.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    self.texts[lang_code] = json.load(f)

    def get_text(self, key: str, lang: str = "ru") -> str:
        return self.texts.get(lang, {}).get(key, f"[{key}]")
