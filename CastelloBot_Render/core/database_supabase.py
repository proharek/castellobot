from supabase import create_client, Client
from datetime import datetime
import json

class DatabaseManager:
    def __init__(self, url: str, key: str):
        self.supabase: Client = create_client(url, key)

    # ===== Пользователи =====

    def get_user_language(self, user_id: int) -> str:
        res = self.supabase.table("users").select("language").eq("user_id", user_id).execute()
        data = res.data
        if data:
            return data[0]["language"]
        return "ru"  # Язык по умолчанию

    def set_user_language(self, user_id: int, lang: str):
        exists = self.supabase.table("users").select("*").eq("user_id", user_id).execute().data
        if exists:
            self.supabase.table("users").update({"language": lang}).eq("user_id", user_id).execute()
        else:
            self.supabase.table("users").insert({"user_id": user_id, "language": lang}).execute()

    # ===== Контракты =====

    def add_contract(self, contract: dict):
        # Убедимся, что нет дубликата по имени
        existing = self.get_contract_by_name(contract["name"])
        if existing:
            # Обновляем контракт, если он есть
            self.update_contract(contract)
            return

        # Преобразуем участников в JSON-строку
        contract_to_insert = contract.copy()
        contract_to_insert["participants"] = json.dumps(contract.get("participants", []))
        self.supabase.table("contracts").insert(contract_to_insert).execute()

    def get_contract_by_name(self, name: str) -> dict | None:
        res = self.supabase.table("contracts").select("*").eq("name", name).execute()
        data = res.data
        if data:
            contract = data[0]
            contract["participants"] = json.loads(contract.get("participants", "[]"))
            return contract
        return None

    def get_all_contracts(self) -> list[dict]:
        res = self.supabase.table("contracts").select("*").execute()
        contracts = res.data or []
        for c in contracts:
            c["participants"] = json.loads(c.get("participants", "[]"))
        return contracts

    def update_contract(self, contract: dict):
        contract_to_update = contract.copy()
        contract_to_update["participants"] = json.dumps(contract.get("participants", []))
        self.supabase.table("contracts").update(contract_to_update).eq("name", contract["name"]).execute()

    def delete_contract_by_name(self, name: str):
        self.supabase.table("contracts").delete().eq("name", name).execute()

    # ===== Отчёты =====

    def add_report(self, report: dict):
        self.supabase.table("reports").insert(report).execute()

    def get_all_reports(self) -> list[dict]:
        res = self.supabase.table("reports").select("*").execute()
        return res.data or []
