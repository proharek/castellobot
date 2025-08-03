import os
import json
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timezone, timedelta
from threading import Thread
from typing import List

import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask, jsonify

from core.database_sqlite import DatabaseManager
from core.language import LanguageManager
from config import Config

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
db = DatabaseManager()
lang_manager = LanguageManager()

# --- Функция загрузки контрактов из JSON ---
def load_contracts_from_json(filepath="contracts.json"):
    if not os.path.exists(filepath):
        print(f"⚠️ JSON файл {filepath} не найден, пропускаем импорт контрактов.")
        return
    with open(filepath, "r", encoding="utf-8") as f:
        contracts = json.load(f)

    count_imported = 0
    for c in contracts:
        name = c.get("name")
        amount = c.get("sum")  # в JSON — sum, в базе — amount
        if not name or not amount:
            continue
        if db.get_contract_by_name(name) is None:
            contract = {
                "name": name,
                "amount": amount,
                "author_id": 0,              # 0 — системный автор
                "author_name": "system",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            db.add_contract(contract)
            count_imported += 1
    print(f"📥 Импортировано {count_imported} контрактов из {filepath}")

# Загрузка контрактов из JSON при старте
load_contracts_from_json()

# --- Flask для Render / UptimeRobot ---
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

# --- UI кнопка для добавления участников (временных) ---
class AddParticipantsButton(discord.ui.Button):
    def __init__(self, contract_name: str, lang: str):
        super().__init__(label="➕ Добавить участников", style=discord.ButtonStyle.primary)
        self.contract_name = contract_name
        self.lang = lang

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            lang_manager.get_text("edit_participants_prompt", self.lang),
            ephemeral=True
        )

        def check(m: discord.Message):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
            mentions = msg.mentions
            await msg.delete()

            if not mentions:
                await interaction.followup.send(lang_manager.get_text("participants_empty", self.lang), ephemeral=True)
                return

            contract = db.get_contract_by_name(self.contract_name)
            if not contract:
                await interaction.followup.send(lang_manager.get_text("contract_not_found", self.lang), ephemeral=True)
                return

            temp_participants = [f"@{u.display_name}" for u in mentions]
            participants_text = "\n".join(f"• {p}" for p in temp_participants)
            fund = contract["amount"] * Config.FUND_PERCENTAGE
            per_user = (contract["amount"] - fund) / len(temp_participants)

            report_text = lang_manager.get_text("report_template", self.lang).format(
                name=contract["name"],
                amount=contract["amount"],
                leader=contract["author_name"],
                participants=participants_text,
                fund=f"{fund:.2f}",
                per_user=f"{per_user:.2f}"
            )

            # Отправка отчёта в канал (для всех)
            await interaction.channel.send(report_text)

            # Автосохранение отчёта в базу
            report = {
                "contract_name": contract["name"],
                "author_id": contract["author_id"],
                "author_name": contract["author_name"],
                "participants": temp_participants,
                "amount": contract["amount"],
                "fund": fund,
                "per_user": per_user,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            db.save_report(report)

            await interaction.followup.send(lang_manager.get_text("report_saved", self.lang).format(name=contract["name"]), ephemeral=True)

        except Exception:
            await interaction.followup.send(lang_manager.get_text("participants_empty", self.lang), ephemeral=True)

# --- Select для выбора контракта ---
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

# --- Команда /addcontract ---
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
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    db.add_contract(contract)
    await interaction.response.send_message(lang_manager.get_text("contract_added", lang).format(name=name, amount=amount))

# --- Команда /editcontract ---
@bot.tree.command(name="editcontract", description="✏️ Редактировать контракт")
@app_commands.describe(name="Название контракта", amount="Новая сумма")
async def edit_contract(interaction: discord.Interaction, name: str, amount: float):
    lang = db.get_user_language(interaction.user.id)
    contract = db.get_contract_by_name(name)
    if not contract:
        await interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return
    if contract.get("author_id") != interaction.user.id:
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return
    if amount <= 0:
        await interaction.response.send_message(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
        return

    contract["amount"] = amount
    db.update_contract(contract)
    await interaction.response.send_message(lang_manager.get_text("contract_updated_success", lang).format(name=name, amount=amount))

# --- Команда /deletecontract ---
@bot.tree.command(name="deletecontract", description="❌ Удалить контракт")
@app_commands.describe(name="Название контракта")
async def delete_contract(interaction: discord.Interaction, name: str):
    lang = db.get_user_language(interaction.user.id)
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return
    contract = db.get_contract_by_name(name)
    if not contract:
        await interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return
    db.delete_contract_by_name(name)
    await interaction.response.send_message(lang_manager.get_text("contract_deleted_success", lang).format(name=name))

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

        participants = []  # Временные участники добавляются через кнопку
        participants_text = "-"

        fund = contract["amount"] * Config.FUND_PERCENTAGE
        per_user = 0

        text = lang_manager.get_text("report_template", lang).format(
            name=contract["name"],
            amount=contract["amount"],
            leader=contract.get("author_name", "N/A"),
            participants=participants_text,
            fund=f"{fund:.2f}",
            per_user=f"{per_user:.2f}"
        )

        view = discord.ui.View()
        view.add_item(AddParticipantsButton(contract["name"], lang))
        await inter.response.edit_message(content=text, embed=None, view=view)

    view = ContractSelectView(contracts, lang, on_select)
    await interaction.response.send_message(lang_manager.get_text("select_contract", lang), view=view, ephemeral=True)

# --- Команда /reportdays ---
@bot.tree.command(name="reportdays", description="📅 Отчёт за последние дни (только для админов)")
@app_commands.describe(days="Количество дней для отчёта (максимум 30)")
async def report_days(interaction: discord.Interaction, days: int = Config.DEFAULT_REPORT_DAYS):
    lang = db.get_user_language(interaction.user.id)
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    if days <= 0 or days > Config.MAX_REPORT_DAYS:
        await interaction.response.send_message(f"❌ Введите число от 1 до {Config.MAX_REPORT_DAYS}.", ephemeral=True)
        return

    reports = db.get_reports_by_days(days)
    if not reports:
        await interaction.response.send_message(lang_manager.get_text("report_not_found", lang), ephemeral=True)
        return

    total_amount = sum(r["amount"] for r in reports)
    total_fund = sum(r["fund"] for r in reports)
    total_payout = sum(r["per_user"] * len(r["participants"]) for r in reports)

    earnings = {}
    for r in reports:
        for p in r["participants"]:
            earnings[p] = earnings.get(p, 0) + r["per_user"]

    earnings_text = "\n".join(f"• {user}: {amount:.2f} USD" for user, amount in earnings.items())

    text = lang_manager.get_text("report_days_summary", lang).format(
        days=days,
        total=total_amount,
        fund=total_fund,
        payout=total_payout,
        earnings=earnings_text
    )
    await interaction.response.send_message(text, ephemeral=True)

# --- Команда /cleanreports ---
@bot.tree.command(name="cleanreports", description="🧹 Удалить отчёты старше N дней (только админ)")
@app_commands.describe(days="Удалить отчёты старше этого количества дней")
async def clean_reports(interaction: discord.Interaction, days: int = Config.REPORT_CLEANUP_DAYS):
    lang = db.get_user_language(interaction.user.id)
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return
    if days <= 0 or days > Config.MAX_REPORT_DAYS:
        await interaction.response.send_message(f"❌ Введите число от 1 до {Config.MAX_REPORT_DAYS}.", ephemeral=True)
        return

    count = db.delete_reports_older_than(days)
    await interaction.response.send_message(f"🧹 Удалено {count} отчётов старше {days} дней.", ephemeral=True)

# --- Команда /language ---
@bot.tree.command(name="language", description="🌐 Сменить язык")
async def change_language(interaction: discord.Interaction):
    lang = db.get_user_language(interaction.user.id)

    class LanguageView(discord.ui.View):
        @discord.ui.button(label=lang_manager.get_text("language_button_ru", lang), style=discord.ButtonStyle.primary)
        async def ru_button(self, interaction_button: discord.Interaction, button: discord.ui.Button):
            db.set_user_language(interaction.user.id, "ru")
            await interaction_button.response.edit_message(content=lang_manager.get_text("language_set_ru", "ru"), view=None)

        @discord.ui.button(label=lang_manager.get_text("language_button_ua", lang), style=discord.ButtonStyle.primary)
        async def ua_button(self, interaction_button: discord.Interaction, button: discord.ui.Button):
            db.set_user_language(interaction.user.id, "ua")
            await interaction_button.response.edit_message(content=lang_manager.get_text("language_set_ua", "ua"), view=None)

    await interaction.response.send_message(lang_manager.get_text("select_language", lang), view=LanguageView(), ephemeral=True)

# --- Команда /info ---
@bot.tree.command(name="info", description="ℹ️ Информация о командах")
async def info(interaction: discord.Interaction):
    lang = db.get_user_language(interaction.user.id)
    text = (
        "📌 **Команды Castello Bot:**\n\n"
        "/language — Сменить язык (RU / UA)\n"
        "/addcontract — Добавить контракт\n"
        "/editcontract — Редактировать контракт (только автор)\n"
        "/deletecontract — Удалить контракт (только админ)\n"
        "/report — Показать отчёт по контракту\n"
        "/reportdays — Сводка за последние дни (только админ)\n"
        "/cleanreports — Удалить отчёты старше N дней (только админ)\n"
        "/info — Информация о командах\n\n"
        "В отчёте доступна кнопка ➕ Добавить участников (временно, без сохранения).\n"
        "После добавления отчёт автоматически сохраняется в базу."
    )
    await interaction.response.send_message(text, ephemeral=True)

# --- Запуск Flask и Discord бота ---
if __name__ == "__main__":
    keep_alive()
    token = Config.DISCORD_BOT_TOKEN
    if not token:
        print("❌ DISCORD_BOT_TOKEN не установлен.")
        exit(1)
    bot.run(token)

