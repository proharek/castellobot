import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Добавить контракт
async def add_contract(name: str, amount: float, author_id: int):
    data = {
        "name": name,
        "amount": amount,
        "author_id": author_id,
        "participants": [author_id]  # всегда сохраняем участника
    }
    supabase.table("contracts").insert(data).execute()

# Получить контракт по названию
async def get_contract_by_name(name: str):
    result = supabase.table("contracts").select("*").eq("name", name).limit(1).execute()
    return result.data[0] if result.data else None

# Получить все контракты
async def get_all_contracts():
    result = supabase.table("contracts").select("*").execute()
    return result.data

# Обновить контракт
async def update_contract(old_name: str, new_name: str, new_amount: float):
    supabase.table("contracts").update({
        "name": new_name,
        "amount": new_amount
    }).eq("name", old_name).execute()

# Удалить контракт
async def delete_contract_by_name(name: str):
    supabase.table("contracts").delete().eq("name", name).execute()

# Установить язык пользователя
async def set_user_language(user_id: int, lang: str):
    existing = supabase.table("languages").select("*").eq("user_id", user_id).execute()
    if existing.data:
        supabase.table("languages").update({"lang": lang}).eq("user_id", user_id).execute()
    else:
        supabase.table("languages").insert({"user_id": user_id, "lang": lang}).execute()

# Получить язык пользователя
async def get_user_language(user_id: int):
    result = supabase.table("languages").select("*").eq("user_id", user_id).limit(1).execute()
    if result.data:
        return result.data[0]["lang"]
    return "ru"  # по умолчанию
