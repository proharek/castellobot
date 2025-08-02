import os
import json
from datetime import datetime, timezone, timedelta
from threading import Thread

import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask, jsonify

from config import Config

# === DatabaseManager с SQLite ===
import sqlite3
from typing import Optional, List

class DatabaseManager:
    def __init__(self, db_path: str = "database.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS contracts (
                    name TEXT PRIMARY KEY,
                    amount REAL,
                    author_id INTEGER,
                    author_name TEXT,
                    participants TEXT,
                    timestamp TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    language TEXT
                )
            """)

    def add_contract(self, contract: dict):
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO contracts (name, amount, author_id, author_name, participants, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                contract["name"],
                contract["amount"],
                contract["author_id"],
                contract["author_name"],
                json.dumps(contract.get("participants", [])),
                contract["timestamp"]
            ))

    def get_contract_by_name(self, name: str) -> Optional[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM contracts WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return {
                "name": row[0],
                "amount": row[1],
                "author_id": row[2],
                "author_name": row[3],
                "participants": json.loads(row[4]) if row[4] else [],
                "timestamp": row[5]
            }
        return None

    def get_all_contracts(self) -> List[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM contracts")
        rows = cur.fetchall()
        return [
            {
                "name": row[0],
                "amount": row[1],
                "author_id": row[2],
                "author_name": row[3],
                "participants": json.loads(row[4]) if row[4] else [],
                "timestamp": row[5]
            }
            for row in rows
        ]

    def update_contract(self, contract: dict):
        with self.conn:
            self.conn.execute("""
                UPDATE contracts
                SET amount = ?, participants = ?, timestamp = ?
                WHERE name = ?
            """, (
                contract["amount"],
                json.dumps(contract.get("participants", [])),
                contract["timestamp"],
                contract["name"]
            ))

    def delete_contract_by_name(self, name: str):
        with self.conn:
            self.conn.execute("DELETE FROM contracts WHERE name = ?", (name,))

    def set_user_language(self, user_id: int, lang: str):
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO users (user_id, language)
                VALUES (?, ?)
            """, (user_id, lang))

    def get_user_language(self, user_id: int) -> str:
        cur = self.conn.cursor()
        cur.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return row[0] if row else Config.DEFAULT_LANGUAGE

# === LanguageManager (очень простой, без файлов) ===
class LanguageManager:
    texts = {
        "ru": {
            "language_set_ru": "Выбран русский язык.",
            "language_set_ua": "Выбран украинский язык.",
            "select_language": "Выберите язык:",
            "menu_title": "📋 Главное меню",
            "menu_description": "Управляй контрактами и настройками через команды ниже.",
            "contract_added": "Контракт **{name}** на сумму **{amount} USD** добавлен.",
            "invalid_amount": "Сумма должна быть положительным числом.",
            "contract_not_found": "Контракт не найден.",
            "contract_updated_success": "Контракт **{name}** обновлён. Новая сумма: **{amount} USD**.",
            "no_permission": "У вас нет прав на редактирование этого контракта.",
            "contract_deleted_success": "Контракт **{name}** успешно удалён.",
            "no_contracts_found": "Контракты не найдены.",
            "select_contract": "Выберите контракт из списка:",
            "report_template": "**📄 Отчёт по контракту \"{name}\"**\n💰 Сумма контракта: {amount} USD\n👤 Старший группы: @{leader}\n👥 Участники:\n{participants}\n🏦 В фонд семьи: {fund} USD (50%)\n💸 Каждому участнику: {per_user} USD",
        },
        "ua": {
            "language_set_ru": "Обрано російську мову.",
            "language_set_ua": "Обрано українську мову.",
            "select_language": "Оберіть мову:",
            "menu_title": "📋 Головне меню",
            "menu_description": "Керуй контрактами та налаштуваннями за допомогою команд нижче.",
            "contract_added": "Контракт **{name}** на суму **{amount} USD** додано.",
            "invalid_amount": "Сума повинна бути додатнім числом.",
            "contract_not_found": "Контракт не знайдено.",
            "contract_updated_success": "Контракт **{name}** оновлено. Нова сума: **{amount} USD**.",
            "no_permission": "У вас немає прав для редагування цього контракту.",
            "contract_deleted_success": "Контракт **{name}** успішно видалено.",
            "no_contracts_found": "Контракти не знайдені.",
            "select_contract": "Оберіть контракт зі списку:",
            "report_template": "**📄 Звіт по контракту \"{name}\"**\n💰 Сума контракту: {amount} USD\n👤 Старший групи: @{leader}\n👥 Учасники:\n{participants}\n🏦 До сімейного фонду: {fund} USD (50%)\n💸 Кожному учаснику: {per_user} USD",
        }
    }

    def get_text(self, key: str, lang: str) -> str:
        return self.texts.get(lang, self.texts[Config.DEFAULT_LANGUAGE]).get(key, f"[{key}]")


# === Инициализация ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=Config.COMMAND_PREFIX, intents=intents)
db = DatabaseManager()
lang_manager = LanguageManager()

# === Flask приложение для /healthz ===
app = Flask('')

@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()}), 200

def run_flask():
    app.run(host=Config.HOST, port=Config.PORT)

def keep_alive():
    Thread(target=run_flask, daemon=True).start()

# === Событие готовности бота ===
@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен.")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Синхронизировано {len(synced)} команд.")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

# === Команда добавить контракт ===
@bot.tree.command(name="addcontract", description="➕ Добавить контракт")
@app_commands.describe(name="Название контракта", amount="Сумма контракта")
async def add_contract(interaction: discord.Interaction, name: str, amount: float):
    lang = db.get_user_language(interaction.user.id)
    if amount <= 0:
        await interaction.response.send_message(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
        return

    contract = {
        "name": name,
        "amount": amount,
        "author_id": interaction.user.id,
        "author_name": interaction.user.display_name,
        "participants": [],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    db.add_contract(contract)
    await interaction.response.send_message(lang_manager.get_text("contract_added", lang).format(name=name, amount=amount))

# === Запуск ===
if __name__ == "__main__":
    keep_alive()
    token = Config.DISCORD_BOT_TOKEN
    if not token:
        print("❌ DISCORD_BOT_TOKEN не установлен.")
        exit(1)
    bot.run(token)
