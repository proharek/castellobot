import os
from supabase import create_client, Client

# Загрузка переменных окружения
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    raise RuntimeError("Ошибка: переменная окружения SUPABASE_URL не установлена или пуста")
if not SUPABASE_KEY:
    raise RuntimeError("Ошибка: переменная окружения SUPABASE_KEY не установлена или пуста")

print(f"Supabase URL: {SUPABASE_URL[:10]}...")  # Показываем начало, чтобы не светить полностью
print(f"Supabase Key: {SUPABASE_KEY[:10]}...")

# Создаем клиент
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Добавить контракт
async def add_contract(name: str, amount: float, author_id: int):
    data = {
        "name": name,
        "amount": amount,
        "author_id": author_id,
        "participants": [author_id]  # всегда сохраняем участника
    }
    response = supabase.table("contracts").insert(data).execute()
    if response.error:
        print(f"Error add_contract: {response.error}")

# Получить контракт по названию
async def get_contract_by_name(name: str):
    response = supabase.table("contracts").select("*").eq("name", name).limit(1).execute()
    if response.error:
        print(f"Error get_contract_by_name: {response.error}")
        return None
    return response.data[0] if response.data else None

# Получить все контракты
async def get_all_contracts():
    response = supabase.table("contracts").select("*").execute()
    if response.error:
        print(f"Error get_all_contracts: {response.error}")
        return []
    return response.data or []

# Обновить контракт
async def update_contract(old_name: str, new_name: str, new_amount: float):
    response = supabase.table("contracts").update({
        "name": new_name,
        "amount": new_amount
    }).eq("name", old_name).execute()
    if response.error:
        print(f"Error update_contract: {response.error}")

# Удалить контракт
async def delete_contract_by_name(name: str):
    response = supabase.table("contracts").delete().eq("name", name).execute()
    if response.error:
        print(f"Error delete_contract_by_name: {response.error}")

# Установить язык пользователя
async def set_user_language(user_id: int, lang: str):
    existing = supabase.table("languages").select("*").eq("user_id", user_id).execute()
    if existing.error:
        print(f"Error set_user_language (select): {existing.error}")
        return
    if existing.data:
        response = supabase.table("languages").update({"lang": lang}).eq("user_id", user_id).execute()
        if response.error:
            print(f"Error set_user_language (update): {response.error}")
    else:
        response = supabase.table("languages").insert({"user_id": user_id, "lang": lang}).execute()
        if response.error:
            print(f"Error set_user_language (insert): {response.error}")

# Получить язык пользователя
async def get_user_language(user_id: int):
    response = supabase.table("languages").select("*").eq("user_id", user_id).limit(1).execute()
    if response.error:
        print(f"Error get_user_language: {response.error}")
        return "ru"
    if response.data:
        return response.data[0]["lang"]
    return "ru"  # по умолчанию

# Сохранить отчёт
async def save_report(report_data: dict):
    response = supabase.table("reports").insert(report_data).execute()
    if response.error:
        print(f"Error save_report: {response.error}")

# Получить все отчёты
async def get_all_reports():
    response = supabase.table("reports").select("*").execute()
    if response.error:
        print(f"Error get_all_reports: {response.error}")
        return []
    return response.data or []
