import aiohttp
import os

class DatabaseManager:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.url = supabase_url
        self.key = supabase_key
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }

    async def set_user_language(self, user_id: int, language: str):
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.url}/rest/v1/users",
                headers=self.headers,
                json={"user_id": user_id, "language": language},
                params={"on_conflict": "user_id"}
            )

    async def get_user_language(self, user_id: int) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.url}/rest/v1/users",
                headers=self.headers,
                params={
                    "user_id": f"eq.{user_id}",
                    "select": "language"
                }
            ) as response:
                data = await response.json()
                if data:
                    return data[0]["language"]
                return "ru"

    async def add_contract(self, name: str, amount: float, leader_id: int, participants: list, created_at: str):
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.url}/rest/v1/contracts",
                headers=self.headers,
                json={
                    "name": name,
                    "amount": amount,
                    "leader_id": leader_id,
                    "participants": participants,
                    "created_at": created_at
                }
            )

    async def get_all_contracts(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.url}/rest/v1/contracts",
                headers=self.headers,
                params={"select": "*"}
            ) as response:
                return await response.json()

    async def get_contract_by_name(self, name: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.url}/rest/v1/contracts",
                headers=self.headers,
                params={
                    "name": f"eq.{name}",
                    "select": "*"
                }
            ) as response:
                data = await response.json()
                return data[0] if data else None

    async def update_contract(self, name: str, new_name: str, new_amount: float):
        async with aiohttp.ClientSession() as session:
            await session.patch(
                f"{self.url}/rest/v1/contracts",
                headers=self.headers,
                params={"name": f"eq.{name}"},
                json={"name": new_name, "amount": new_amount}
            )

    async def delete_contract_by_name(self, name: str):
        async with aiohttp.ClientSession() as session:
            await session.delete(
                f"{self.url}/rest/v1/contracts",
                headers=self.headers,
                params={"name": f"eq.{name}"}
            )

    async def save_report(self, content: str, author_id: int, contract_name: str, created_at: str):
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.url}/rest/v1/reports",
                headers=self.headers,
                json={
                    "content": content,
                    "author_id": author_id,
                    "contract_name": contract_name,
                    "created_at": created_at
                }
            )

    async def get_all_reports(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.url}/rest/v1/reports",
                headers=self.headers,
                params={"select": "*"}
            ) as response:
                return await response.json()
