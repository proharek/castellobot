import os
import json
from datetime import datetime, timedelta

class DatabaseManager:
    def __init__(self):
        self.contracts_file = "contracts_data.json"
        self.reports_file = "reports_data.json"
        self.languages_file = "user_languages.json"

        self.contracts = []
        self.reports = []
        self.user_languages = {}

        self.load_all()

    def load_all(self):
        self.load_contracts_from_file()
        self.load_reports_from_file()
        self.load_user_languages()

    # --- Контракты ---

    def load_contracts_from_file(self):
        if os.path.exists(self.contracts_file):
            with open(self.contracts_file, "r", encoding="utf-8") as f:
                self.contracts = json.load(f)
        else:
            self.contracts = []

    def save_contracts_to_file(self):
        with open(self.contracts_file, "w", encoding="utf-8") as f:
            json.dump(self.contracts, f, ensure_ascii=False, indent=2)

    def add_contract(self, contract: dict):
        self.contracts.append(contract)
        self.save_contracts_to_file()

    def update_contract(self, contract: dict):
        for i, c in enumerate(self.contracts):
            if c["name"] == contract["name"]:
                self.contracts[i] = contract
                break
        self.save_contracts_to_file()

    def delete_contract_by_name(self, name: str):
        self.contracts = [c for c in self.contracts if c["name"] != name]
        self.save_contracts_to_file()

    def get_all_contracts(self):
        return self.contracts

    def get_contract_by_name(self, name: str):
        return next((c for c in self.contracts if c["name"] == name), None)

    # --- Отчёты ---

    def load_reports_from_file(self):
        if os.path.exists(self.reports_file):
            with open(self.reports_file, "r", encoding="utf-8") as f:
                self.reports = json.load(f)
        else:
            self.reports = []

    def save_reports_to_file(self):
        with open(self.reports_file, "w", encoding="utf-8") as f:
            json.dump(self.reports, f, ensure_ascii=False, indent=2)

    def save_report(self, report: dict):
        # Проверка: не дублировать один и тот же отчёт
        for r in self.reports:
            if r["contract_name"] == report["contract_name"]:
                return False  # Уже есть
        self.reports.append(report)
        self.save_reports_to_file()
        return True

    def get_reports_by_days(self, days: int):
        cutoff = datetime.utcnow() - timedelta(days=days)
        return [
            r for r in self.reports
            if datetime.fromisoformat(r["timestamp"]).replace(tzinfo=None) >= cutoff
        ]

    def clean_old_reports(self, days: int = 7) -> int:
        """Удалить из базы отчёты старше N дней. Вернуть количество удалённых."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        before = len(self.reports)
        self.reports = [
            r for r in self.reports
            if datetime.fromisoformat(r["timestamp"]).replace(tzinfo=None) >= cutoff
        ]
        self.save_reports_to_file()
        return before - len(self.reports)

    # --- Язык пользователя ---

    def load_user_languages(self):
        if os.path.exists(self.languages_file):
            with open(self.languages_file, "r", encoding="utf-8") as f:
                self.user_languages = json.load(f)
        else:
            self.user_languages = {}

    def save_user_languages(self):
        with open(self.languages_file, "w", encoding="utf-8") as f:
            json.dump(self.user_languages, f, ensure_ascii=False, indent=2)

    def set_user_language(self, user_id: int, language: str):
        self.user_languages[str(user_id)] = language
        self.save_user_languages()

    def get_user_language(self, user_id: int):
        return self.user_languages.get(str(user_id), "ru")
