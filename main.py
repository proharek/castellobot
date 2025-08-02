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

# --- База данных на SQLite ---
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
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_name TEXT,
                    amount REAL,
                    leader_id INTEGER,
                    leader_name TEXT,
                    participants TEXT,
                    fund REAL,
                    per_user REAL,
                    timestamp TEXT
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

    def save_report(self, report: dict):
        with self.conn:
            self.conn.execute("""
                INSERT INTO reports (contract_name, amount, leader_id, leader_name, participants, fund, per_user, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report["contract_name"],
                report["amount"],
                report["leader_id"],
                report["leader_name"],
                json.dumps(report["participants"]),
                report["fund"],
                report["per_user"],
                report["timestamp"]
            ))

    def get_reports_since(self, since: datetime) -> List[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM reports WHERE timestamp >= ?", (since.isoformat(),))
        rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "contract_name": row[1],
                "amount": row[2],
                "leader_id": row[3],
                "leader_name": row[4],
                "participants": json.loads(row[5]) if row[5] else [],
                "fund": row[6],
                "per_user": row[7],
                "timestamp": row[8],
            }
            for row in rows
        ]

# --- Языки (тексты) ---
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
            "language_changed": "Язык изменён на {language}.",
            "participants_added": "Участники добавлены во временный список для контракта **{name}**.",
            "edit_participants_prompt": "Отправьте теги участников через пробел.",
            "participants_empty": "Список участников не может быть пустым.",
            "reportdays_no_reports": "За указанный период отчётов не найдено.",
            "reportdays_summary": "📅 Отчёты за последние {days} дней:\nОбщая сумма: {total_amount} USD\nУчастники:\n{participants_summary}",
            "reportdays_participant_line": "• {user}: {amount:.2f} USD",
            "report_saved": "Отчёт по контракту **{name}** успешно сохранён.",
            "no_reports_found": "Отчёты не найдены.",
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
            "language_changed": "Мову змінено на {language}.",
            "participants_added": "Учасники додані до тимчасового списку для контракту **{name}**.",
            "edit_participants_prompt": "Надішліть теги учасників через пробіл.",
            "participants_empty": "Список учасників не може бути порожнім.",
            "reportdays_no_reports": "За вказаний період звітів не знайдено.",
            "reportdays_summary": "📅 Звіти за останні {days} днів:\nЗагальна сума: {total_amount} USD\nУчасники:\n{participants_summary}",
            "reportdays_participant_line": "• {user}: {amount:.2f} USD",
            "report_saved": "Звіт по контракту **{name}** успішно збережено.",
            "no_reports_found": "Звіти не знайдено.",
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

# --- Flask для /healthz ---
app = Flask('')

@app.route('/')
def index():
    return jsonify({"status": "bot is running"}), 200

@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()}), 200

def run_flask():
    app.run(host=Config.HOST, port=Config.PORT)

def keep_alive():
    Thread(target=run_flask, daemon=True).start()

# --- View для выбора контракта ---
class ContractSelect(discord.ui.Select):
    def __init__(self, contracts: List[dict], lang: str, callback):
        options = [
            discord.SelectOption(label=c["name"], description=f'{c["amount"]} USD', value=c["name"])
            for c in contracts[:Config.MAX_CONTRACTS_DISPLAY]
        ]
        super().__init__(placeholder=lang_manager.get_text("select_contract", lang), options=options)
        self.callback_func = callback
        self.lang = lang

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.values[0], self.lang)

class ContractSelectView(discord.ui.View):
    def __init__(self, contracts: List[dict], lang: str, callback):
        super().__init__(timeout=120)
        self.add_item(ContractSelect(contracts, lang, callback))

# --- Кнопка "➕ Добавить участников" (Временные участники, не сохраняются в БД) ---
class AddParticipantsButton(discord.ui.Button):
    def __init__(self, contract: dict, lang: str, report_state: dict):
        super().__init__(label="➕ Добавить участников", style=discord.ButtonStyle.primary)
        self.contract = contract
        self.lang = lang
        self.report_state = report_state  # dict для хранения временных участников

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

            # Обновляем временных участников в report_state (не сохраняем в БД)
            self.report_state["participants"] = [f"@{u.display_name}" for u in mentions]

            await interaction.followup.send(lang_manager.get_text("participants_added", self.lang).format(name=self.contract["name"]), ephemeral=True)

            # После добавления участников обновим сообщение отчёта с новыми участниками и расчётами
            fund = self.contract["amount"] * Config.FUND_PERCENTAGE
            per_user = 0
            if self.report_state["participants"]:
                per_user = (self.contract["amount"] - fund) / len(self.report_state["participants"])
            participants_text = "\n".join(f"• {p}" for p in self.report_state["participants"])

            text = lang_manager.get_text("report_template", self.lang).format(
                name=self.contract["name"],
                amount=self.contract["amount"],
                leader=self.contract["author_name"],
                participants=participants_text,
                fund=f"{fund:.2f}",
                per_user=f"{per_user:.2f}"
            )

            # Обновляем сообщение с отчётом, показываем кнопку опять
            view = discord.ui.View(timeout=180)
            view.add_item(self)

            await interaction.message.edit(content=text, view=view)

        except Exception:
            await interaction.followup.send(lang_manager.get_text("participants_empty", self.lang), ephemeral=True)

# --- Команда смены языка ---
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

# --- Команда добавить контракт ---
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

# --- Команда показать меню ---
@bot.tree.command(name="menu", description="📋 Главное меню")
async def menu(interaction: discord.Interaction):
    lang = db.get_user_language(interaction.user.id)
    contracts = db.get_all_contracts()

    description = lang_manager.get_text("menu_description", lang)
    embed = discord.Embed(title=lang_manager.get_text("menu_title", lang), description=description, color=discord.Color.blue())
    if contracts:
        for c in contracts[:Config.MAX_CONTRACTS_DISPLAY]:
            embed.add_field(name=c["name"], value=f'Сумма: {c["amount"]} USD\nАвтор: {c["author_name"]}\nУчастники: {", ".join(c["participants"]) if c["participants"] else "-"}', inline=False)
    else:
        embed.description += f"\n\n{lang_manager.get_text('no_contracts_found', lang)}"

    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Команда отчёт ---
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

        # Начинаем с участников из контракта, но будем менять временно
        report_state = {
            "participants": contract["participants"][:],  # копия списка
        }

        fund = contract["amount"] * Config.FUND_PERCENTAGE
        per_user = 0
        if report_state["participants"]:
            per_user = (contract["amount"] - fund) / len(report_state["participants"])
        participants_text = "\n".join(f"• {p}" for p in report_state["participants"]) if report_state["participants"] else "-"

        text = lang_manager.get_text("report_template", lang).format(
            name=contract["name"],
            amount=contract["amount"],
            leader=contract["author_name"],
            participants=participants_text,
            fund=f"{fund:.2f}",
            per_user=f"{per_user:.2f}"
        )

        view = discord.ui.View(timeout=180)
        view.add_item(AddParticipantsButton(contract, lang, report_state))

        await inter.response.edit_message(content=text, embed=None, view=view)

    view = ContractSelectView(contracts, lang, on_select)
    await interaction.response.send_message(lang_manager.get_text("select_contract", lang), view=view, ephemeral=True)

# --- Команда редактировать контракт ---
@bot.tree.command(name="editcontract", description="✏️ Редактировать контракт (название и сумму)")
@app_commands.describe(name="Название контракта", new_name="Новое название", new_amount="Новая сумма")
async def edit_contract(interaction: discord.Interaction, name: str, new_name: str, new_amount: float):
    lang = db.get_user_language(interaction.user.id)
    contract = db.get_contract_by_name(name)
    if not contract:
        await interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return
    if interaction.user.id != contract["author_id"]:
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return
    if new_amount <= 0:
        await interaction.response.send_message(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
        return

    # Удаляем старый контракт и добавляем новый с новым именем и суммой
    db.delete_contract_by_name(name)
    contract["name"] = new_name
    contract["amount"] = new_amount
    contract["timestamp"] = datetime.now(timezone.utc).isoformat()
    db.add_contract(contract)

    await interaction.response.send_message(lang_manager.get_text("contract_updated_success", lang).format(name=new_name, amount=new_amount))

# --- Команда удалить контракт ---
@bot.tree.command(name="deletecontract", description="❌ Удалить контракт")
@app_commands.describe(name="Название контракта")
async def delete_contract(interaction: discord.Interaction, name: str):
    lang = db.get_user_language(interaction.user.id)
    contract = db.get_contract_by_name(name)
    if not contract:
        await interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return

    # Разрешаем удалять контракт только автору или администратору сервера
    if interaction.user.id != contract["author_id"]:
        # Проверка на права администратора
        guild = interaction.guild
        member = guild.get_member(interaction.user.id)
        if not member.guild_permissions.administrator:
            await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
            return

    db.delete_contract_by_name(name)
    await interaction.response.send_message(lang_manager.get_text("contract_deleted_success", lang).format(name=name))

# --- Команда /reportdays (отчёты за последние N дней) ---
@bot.tree.command(name="reportdays", description="📅 Отчёты за последние дни")
@app_commands.describe(days="Количество дней для отчётов")
async def reportdays(interaction: discord.Interaction, days: int):
    lang = db.get_user_language(interaction.user.id)
    if days <= 0:
        await interaction.response.send_message(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
        return

    since = datetime.now(timezone.utc) - timedelta(days=days)
    reports = db.get_reports_since(since)
    if not reports:
        await interaction.response.send_message(lang_manager.get_text("reportdays_no_reports", lang), ephemeral=True)
        return

    total_amount = 0
    participant_sums = {}

    for rep in reports:
        total_amount += rep["amount"]
        for p in rep["participants"]:
            participant_sums[p] = participant_sums.get(p, 0) + rep["per_user"]

    participants_summary = "\n".join(
        lang_manager.get_text("reportdays_participant_line", lang).format(user=user, amount=amt)
        for user, amt in participant_sums.items()
    )

    summary = lang_manager.get_text("reportdays_summary", lang).format(
        days=days,
        total_amount=f"{total_amount:.2f}",
        participants_summary=participants_summary
    )

    await interaction.response.send_message(summary, ephemeral=True)

# --- Запуск ---
if __name__ == "__main__":
    keep_alive()
    token = Config.DISCORD_BOT_TOKEN
    if not token:
        print("❌ DISCORD_BOT_TOKEN не установлен.")
        exit(1)
    bot.run(token)
