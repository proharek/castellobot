import asyncio
from supabase import create_client, Client

class DatabaseManager:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase: Client = create_client(supabase_url, supabase_key)

    async def get_user_language(self, user_id: int) -> str:
        loop = asyncio.get_running_loop()

        def query_language():
            try:
                res = self.supabase.table("users").select("language").eq("user_id", user_id).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0].get("language", "ru") or "ru"
                return "ru"
            except Exception as e:
                print(f"Ошибка получения языка: {e}")
                return "ru"

        return await loop.run_in_executor(None, query_language)

    async def set_user_language(self, user_id: int, language: str):
        loop = asyncio.get_running_loop()

        def query_set_language():
            try:
                res = self.supabase.table("users").select("user_id").eq("user_id", user_id).execute()
                if res.data and len(res.data) > 0:
                    self.supabase.table("users").update({"language": language}).eq("user_id", user_id).execute()
                else:
                    self.supabase.table("users").insert({"user_id": user_id, "language": language}).execute()
            except Exception as e:
                print(f"Ошибка установки языка: {e}")

        await loop.run_in_executor(None, query_set_language)

    async def add_contract(self, contract: dict):
        loop = asyncio.get_running_loop()

        def query_add_contract():
            try:
                self.supabase.table("contracts").insert(contract).execute()
            except Exception as e:
                print(f"Ошибка добавления контракта: {e}")

        await loop.run_in_executor(None, query_add_contract)

    async def get_contract_by_name(self, name: str):
        loop = asyncio.get_running_loop()

        def query_get_contract():
            try:
                res = self.supabase.table("contracts").select("*").eq("name", name).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
                return None
            except Exception as e:
                print(f"Ошибка получения контракта: {e}")
                return None

        return await loop.run_in_executor(None, query_get_contract)

    async def get_all_contracts(self):
        loop = asyncio.get_running_loop()

        def query_all_contracts():
            try:
                res = self.supabase.table("contracts").select("*").execute()
                return res.data if res.data else []
            except Exception as e:
                print(f"Ошибка получения всех контрактов: {e}")
                return []

        return await loop.run_in_executor(None, query_all_contracts)

    async def update_contract(self, contract: dict):
        loop = asyncio.get_running_loop()

        def query_update():
            try:
                self.supabase.table("contracts").update(contract).eq("name", contract["name"]).execute()
            except Exception as e:
                print(f"Ошибка обновления контракта: {e}")

        await loop.run_in_executor(None, query_update)

    async def delete_contract_by_name(self, name: str):
        loop = asyncio.get_running_loop()

        def query_delete():
            try:
                self.supabase.table("contracts").delete().eq("name", name).execute()
            except Exception as e:
                print(f"Ошибка удаления контракта: {e}")

        await loop.run_in_executor(None, query_delete)

    async def save_report(self, report: dict):
        loop = asyncio.get_running_loop()

        def query_save_report():
            try:
                self.supabase.table("reports").insert(report).execute()
            except Exception as e:
                print(f"Ошибка сохранения отчёта: {e}")

        await loop.run_in_executor(None, query_save_report)

    async def get_all_reports(self):
        loop = asyncio.get_running_loop()

        def query_all_reports():
            try:
                res = self.supabase.table("reports").select("*").order("timestamp", desc=True).execute()
                return res.data if res.data else []
            except Exception as e:
                print(f"Ошибка получения отчётов: {e}")
                return []

        return await loop.run_in_executor(None, query_all_reports)
