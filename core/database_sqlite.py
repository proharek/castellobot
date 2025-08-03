import json
import os
from datetime import datetime, timezone, timedelta

class DatabaseManager:
    def __init__(self):
        self.contracts_file = "contracts_data.json"
        self.reports_file = "reports_data.json"
        self.users_file = "users_lang.json"
        self._ensure_files()

    def _ensure_files(self):
        for file in [self.contracts_file, self.reports_file, self.users_file]:
            if not os.path.exists(file):
                with open(file, "w", encoding="utf-8") as f:
                    json.dump([], f) if "reports" in file or "contracts" in file else json.dump({}, f)

    def load_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all_contracts(self):
        return self.load_json(self.contracts_file)

    def get_contract_by_name(self, name):
        return next((c for c in self.get_all_contracts() if c["name"] == name), None)

    def add_contract(self, contract):
        contracts = self.get_all_contracts()
        contracts.append(contract)
        self.save_json(self.contracts_file, contracts)

    def update_contract(self, updated):
        contracts = self.get_all_contracts()
        for i, c in enumerate(contracts):
            if c["name"] == updated["name"]:
                contracts[i] = updated
                break
        self.save_json(self.contracts_file, contracts)

    def delete_contract_by_name(self, name):
        contracts = [c for c in self.get_all_contracts() if c["name"] != name]
        self.save_json(self.contracts_file, contracts)

    def save_report(self, report):
        reports = self.load_json(self.reports_file)
        if any(r["contract_name"] == report["contract_name"] for r in reports):
            return False
        reports.append(report)
        self.save_json(self.reports_file, reports)
        return True

    def get_reports_by_days(self, days):
        reports = self.load_json(self.reports_file)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return [r for r in reports if datetime.fromisoformat(r["timestamp"]) >= cutoff]

    def get_user_language(self, user_id: int):
        users = self.load_json(self.users_file)
        return users.get(str(user_id), "ru")

    def set_user_language(self, user_id: int, lang: str):
        users = self.load_json(self.users_file)
        users[str(user_id)] = lang
        self.save_json(self.users_file, users)
