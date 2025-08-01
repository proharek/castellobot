import os
from supabase import create_client, Client
from typing import Optional

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Добавить контракт
def add_contract(name: str, amount: float, author_id: int):
    data = {
        "name": name,
        "amount": amount,
        "author_id": author_id,
        "participants": [author_id]
    }
    supabase.table("contracts").insert(data).execute()

# Получить контракт по названию
def get_contract_by_name(name: str) -> Optional[dict]:
    result = supabase.table("contracts").select("*").eq("name", name).limit(1).execute()
    return result.data[0] if result.data else None

# Получить все контракты
def get_all_contracts() -> list:
    result = supabase.table("contracts").select("*").execute()
    return result.data

# Обновить контракт
def update_contract(old_name: str, new_name: str, new_amount: float):
    supabase.table("contracts").update({
        "name": new_name,
        "amount": new_amount
    }).eq("name", old_name).execute()

# Удалить контракт
def delete_contract_by_name(name: str):
    supabase.table("contracts").delete().eq("name", name).execute()

# Установить язык пользователя
def set_user_language(user_id: int, lang: str):
    existing = supabase.table("languages").select("*").eq("user_id", user_id).execute()
    if existing.data:
        supabase.table("languages").update({"lang": lang}).eq("user_id", user_id).execute()
    else:
        supabase.table("languages").insert({"user_id": user_id, "lang": lang}).execute()

# Получить язык пользователя
def get_user_language(user_id: int) -> str:
    result = supabase.table("languages").select("*").eq("user_id", user_id).limit(1).execute()
    if result.data:
        return result.data[0]["lang"]
    return "ru"

# Сохранить текстовый отчёт
def save_report(text: str):
    supabase.table("reports").insert({"text": text}).execute()

# Получить все отчёты
def get_all_reports() -> list:
    result = supabase.table("reports").select("*").execute()
    return result.data

