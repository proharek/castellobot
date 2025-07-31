import asyncio
from supabase import create_client

class DatabaseManager:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase = create_client(supabase_url, supabase_key)

    # Добавить контракт
    async def add_contract(self, contract: dict):
        loop = asyncio.get_running_loop()
        def insert_contract():
            res = self.supabase.table("contracts").upsert(contract).execute()
            if res.error:
                print(f"Ошибка добавления контракта: {res.error}")
        await loop.run_in_executor(None, insert_contract)

    # Получить контракт по имени
    async def get_contract_by_name(self, name: str) -> dict | None:
        loop = asyncio.get_running_loop()
        def query_contract():
            res = self.supabase.table("contracts").select("*").eq("name", name).execute()
            if res.error:
                print(f"Ошибка получения контракта: {res.error}")
                return None
            if res.data:
                return res.data[0]
            return None
        return await loop.run_in_executor(None, query_contract)

    # Получить все контракты
    async def get_all_contracts(self) -> list:
        loop = asyncio.get_running_loop()
        def query_all():
            res = self.supabase.table("contracts").select("*").execute()
            if res.error:
                print(f"Ошибка получения всех контрактов: {res.error}")
                return []
            return res.data
        return await loop.run_in_executor(None, query_all)

    # Обновить контракт
    async def update_contract(self, contract: dict):
        loop = asyncio.get_running_loop()
        def update():
            res = self.supabase.table("contracts").update(contract).eq("name", contract["name"]).execute()
            if res.error:
                print(f"Ошибка обновления контракта: {res.error}")
        await loop.run_in_executor(None, update)

    # Удалить контракт по имени
    async def delete_contract_by_name(self, name: str):
        loop = asyncio.get_running_loop()
        def delete():
            res = self.supabase.table("contracts").delete().eq("name", name).execute()
            if res.error:
                print(f"Ошибка удаления контракта: {res.error}")
        await loop.run_in_executor(None, delete)

    # Установить язык пользователя
    async def set_user_language(self, user_id: int, lang: str):
        loop = asyncio.get_running_loop()
        def upsert_language():
            data = {"user_id": user_id, "language": lang}
            res = self.supabase.table("users").upsert(data).execute()
            if res.error:
                print(f"Ошибка установки языка: {res.error}")
        await loop.run_in_executor(None, upsert_language)

    # Получить язык пользователя
    async def get_user_language(self, user_id: int) -> str:
        loop = asyncio.get_running_loop()
        def query_language():
            res = self.supabase.table("users").select("language").eq("user_id", user_id).execute()
            if res.error:
                print(f"Ошибка получения языка: {res.error}")
                return None
            if res.data and len(res.data) > 0:
                return res.data[0]["language"]
            return "ru"
        return await loop.run_in_executor(None, query_language)

    # Сохранить отчёт
    async def save_report(
        self,
        contract_name: str,
        amount: float,
        participants: list[str],
        leader: str,
        fund: float,
        per_user: float,
        message: str,
    ):
        loop = asyncio.get_running_loop()
        def insert_report():
            data = {
                "contract_name": contract_name,
                "amount": amount,
                "participants": "\n".join(participants),
                "leader": leader,
                "fund": fund,
                "per_user": per_user,
                "message": message,
            }
            res = self.supabase.table("reports").insert(data).execute()
            if res.error:
                print(f"Ошибка сохранения отчёта: {res.error}")
        await loop.run_in_executor(None, insert_report)

    # Получить все отчёты
    async def get_all_reports(self) -> list:
        loop = asyncio.get_running_loop()
        def query_reports():
            res = self.supabase.table("reports").select("*").order("created_at", desc=True).execute()
            if res.error:
                print(f"Ошибка получения отчётов: {res.error}")
                return []
            return res.data
        return await loop.run_in_executor(None, query_reports)

