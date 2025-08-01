import os
import asyncio
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL и SUPABASE_KEY должны быть установлены в переменных окружения")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


async def add_contract(name: str, amount: float, author_id: int):
    data = {
        "name": name,
        "amount": amount,
        "author_id": author_id,
        "participants": [author_id]
    }
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: supabase.table("contracts").insert(data).execute())


async def get_contract_by_name(name: str):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: supabase.table("contracts").select("*").eq("name", name).limit(1).execute())
    return result.data[0] if result.data else None


async def get_all_contracts():
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: supabase.table("contracts").select("*").execute())
    return result.data


async def update_contract(old_name: str, new_name: str, new_amount: float):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: supabase.table("contracts").update({
        "name": new_name,
        "amount": new_amount
    }).eq("name", old_name).execute())


async def delete_contract_by_name(name: str):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: supabase.table("contracts").delete().eq("name", name).execute())


async def set_user_language(user_id: int, lang: str):
    loop = asyncio.get_running_loop()
    existing = await loop.run_in_executor(None, lambda: supabase.table("languages").select("*").eq("user_id", user_id).execute())
    if existing.data:
        await loop.run_in_executor(None, lambda: supabase.table("languages").update({"lang": lang}).eq("user_id", user_id).execute())
    else:
        await loop.run_in_executor(None, lambda: supabase.table("languages").insert({"user_id": user_id, "lang": lang}).execute())


async def get_user_language(user_id: int):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: supabase.table("languages").select("*").eq("user_id", user_id).limit(1).execute())
    if result.data:
        return result.data[0]["lang"]
    return "ru"
