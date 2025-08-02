import os
import json
from datetime import datetime, timezone
from threading import Thread
from typing import List, Optional

import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask, jsonify

# --- Конфиг ---
class Config:
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    DEFAULT_LANGUAGE = "ru"
    SUPPORTED_LANGUAGES = ["ru", "ua"]
    FUND_PERCENTAGE = 0.5
    HOST = "0.0.0.0"
    PORT = 8080
    COMMAND_PREFIX = "!"
    MAX_CONTRACTS_DISPLAY = 25

# --- SQLite ---
import sqlite3

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
                INSERT OR REPLACE INTO contracts
                (name, amount, author_id, author_name, participants, timestamp)
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

# --- Языки ---
class LanguageManager:
    texts = {
        "ru": {
            "language_set_ru": "Выбран русский язык.",
            "language_set_ua": "Выбран украинский язык.",
            "select_language": "Выберите контракт из списка:",
            "report_template": "**📄 Отчёт по контракту \"{name}\"**\n💰 Сумма контракта: {amount} USD\n👤 Старший группы: @{leader}\n👥 Участники:\n{participants}\n🏦 В фонд семьи: {fund} USD (50%)\n💸 Каждому участнику: {per_user} USD",
            "no_contracts_found": "Контракты не найдены.",
            "contract_not_found": "Контракт не найден.",
            "edit_participants_prompt": "Отправьте теги участников через пробел.",
            "participants_empty": "Список участников не может быть пустым.",
            "participants_added": "Участники добавлены в контракт **{name}**.",
            "no_permission": "У вас нет прав на редактирование этого контракта.",
        },
        "ua": {
            "language_set_ru": "Обрано російську мову.",
            "language_set_ua": "Обрано українську мову.",
            "select_language": "Оберіть контракт зі списку:",
            "report_template": "**📄 Звіт по контракту \"{name}\"**\n💰 Сума контракту: {amount} USD\n👤 Старший групи: @{leader}\n👥 Учасники:\n{participants}\n🏦 До сімейного фонду: {fund} USD (50%)\n💸 Кожному учаснику: {per_user} USD",
            "no_contracts_found": "Контракти не знайдені.",
            "contract_not_found": "Контракт не знайдено.",
            "edit_participants_prompt": "Надішліть теги учасників через пробіл.",
            "participants_empty": "Список учасників не може бути порожнім.",
            "participants_added": "Учасники додані до контракту **{name}**.",
            "no_permission": "У вас немає прав для редагування цього контракту.",
        }
    }

    def get_text(self, key: str, lang: str) -> str:
        return self.texts.get(lang, self.texts[Config.DEFAULT_LANGUAGE]).get(key, f"[{key}]")

# --- Инициализация ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=Config.COMMAND_PREFIX, intents=intents)
db = DatabaseManager()
lang_manager = LanguageManager()

app = Flask('')

@app.route('/')
def index():
    return jsonify({"status": "bot is running"}), 200

def run_flask():
    app.run(host=Config.HOST, port=Config.PORT)

def keep_alive():
    Thread(target=run_flask, daemon=True).start()
# --- View выбора контракта ---
class ContractSelect(discord.ui.Select):
    def __init__(self, contracts: List[dict], lang: str, callback):
        options = [
            discord.SelectOption(label=c["name"], description=f'{c["amount"]} USD', value=c["name"])
            for c in contracts[:Config.MAX_CONTRACTS_DISPLAY]
        ]
        super().__init__(placeholder=lang_manager.get_text("select_language", lang), options=options)
        self.callback_func = callback
        self.lang = lang

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.values[0], self.lang)

class ContractSelectView(discord.ui.View):
    def __init__(self, contracts: List[dict], lang: str, callback):
        super().__init__(timeout=120)
        self.add_item(ContractSelect(contracts, lang, callback))

# --- Кнопка "➕ Добавить участников" ---
class TempAddParticipantsButton(discord.ui.Button):
    def __init__(self, contract: dict, lang: str, original_interaction: discord.Interaction):
        super().__init__(label="➕ Добавить участников", style=discord.ButtonStyle.primary)
        self.contract = contract
        self.lang = lang
        self.original_interaction = original_interaction

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.contract["author_id"]:
            await interaction.response.send_message(lang_manager.get_text("no_permission", self.lang), ephemeral=True)
            return

        await interaction.response.send_message(lang_manager.get_text("edit_participants_prompt", self.lang), ephemeral=True)

        def check(m: discord.Message):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
            mentions = msg.mentions
            if not mentions:
                await interaction.followup.send(lang_manager.get_text("participants_empty", self.lang), ephemeral=True)
                return

            temp_participants = [f"@{u.display_name}" for u in mentions]
            fund = self.contract["amount"] * Config.FUND_PERCENTAGE
            per_user = (self.contract["amount"] - fund) / len(temp_participants)

            participants_text = "\n".join(f"• {p}" for p in temp_participants)
            text = lang_manager.get_text("report_template", self.lang).format(
                name=self.contract["name"],
                amount=self.contract["amount"],
                leader=self.contract["author_name"],
                participants=participants_text,
                fund=f"{fund:.2f}",
                per_user=f"{per_user:.2f}"
            )

            await interaction.followup.send(text, ephemeral=True)
        except Exception:
            await interaction.followup.send(lang_manager.get_text("participants_empty", self.lang), ephemeral=True)

# --- Команда /report ---
@bot.tree.command(name="report", description="📄 Отчёт по контракту")
async def report(interaction: discord.Interaction):
    lang = db.get_user_language(interaction.user.id)
    contracts = db.get_all_contracts()
    if not contracts:
        await interaction.response.send_message(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    async def on_select(inter: discord.Interaction, contract_name: str, lang: str):
        contract = db.get_contract_by_name(contract_name)
        if not contract:
            await inter.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
            return

        participants_text = "\n".join(f"• {p}" for p in contract["participants"]) if contract["participants"] else "-"
        fund = contract["amount"] * Config.FUND_PERCENTAGE
        per_user = (contract["amount"] - fund) / len(contract["participants"]) if contract["participants"] else 0

        text = lang_manager.get_text("report_template", lang).format(
            name=contract["name"],
            amount=contract["amount"],
            leader=contract["author_name"],
            participants=participants_text,
            fund=f"{fund:.2f}",
            per_user=f"{per_user:.2f}"
        )

        view = discord.ui.View(timeout=180)
        view.add_item(TempAddParticipantsButton(contract, lang, inter))

        await inter.response.edit_message(content=text, embed=None, view=view)

    view = ContractSelectView(contracts, lang, on_select)
    await interaction.response.send_message(lang_manager.get_text("select_language", lang), view=view, ephemeral=True)

# --- Команда /language ---
@bot.tree.command(name="language", description="🌐 Сменить язык")
@app_commands.choices(language=[
    app_commands.Choice(name="Русский", value="ru"),
    app_commands.Choice(name="Українська", value="ua"),
])
async def change_language(interaction: discord.Interaction, language: app_commands.Choice[str]):
    db.set_user_language(interaction.user.id, language.value)
    await interaction.response.send_message(
        lang_manager.get_text(f"language_set_{language.value}", language.value),
        ephemeral=True
    )

# --- Синхронизация ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Бот запущен как {bot.user} (ID: {bot.user.id})")

# --- Запуск ---
if __name__ == "__main__":
    keep_alive()
    token = Config.DISCORD_BOT_TOKEN
    if not token:
        print("❌ DISCORD_BOT_TOKEN не установлен.")
        exit(1)
    bot.run(token)
