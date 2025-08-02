import os
import json
from datetime import datetime, timezone, timedelta
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

# --- Database ---
from core import database

db = database.DatabaseManager()

# --- Языки (тексты) ---
from core import language

lang_manager = language.LanguageManager()

# --- Инициализация бота ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=Config.COMMAND_PREFIX, intents=intents)

# --- Flask ---
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

        participants = "\n".join(f"• {p}" for p in contract["participants"]) if contract["participants"] else "-"

        fund = contract["amount"] * Config.FUND_PERCENTAGE
        per_user = 0
        if contract["participants"]:
            per_user = (contract["amount"] - fund) / len(contract["participants"])

        # Добавляем кнопку "➕ Добавить участников"
        class AddParticipantsButton(discord.ui.Button):
            def __init__(self):
                super().__init__(label="➕ Добавить участников", style=discord.ButtonStyle.primary)

            async def callback(self, button_interaction: discord.Interaction):
                await button_interaction.response.send_message(
                    "Отправьте через пробел теги участников (например, @User1 @User2):",
                    ephemeral=True
                )

                def check(m: discord.Message):
                    return m.author == button_interaction.user and m.channel == button_interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=60)
                    mentions = msg.mentions
                    if not mentions:
                        await button_interaction.followup.send(lang_manager.get_text("participants_empty", lang), ephemeral=True)
                        return

                    # Временные участники, не сохраняем в базу, просто обновляем сообщение отчёта
                    temp_participants = [f"@{u.display_name}" for u in mentions]

                    participants_text = "\n".join(f"• {p}" for p in temp_participants)

                    fund_local = contract["amount"] * Config.FUND_PERCENTAGE
                    per_user_local = (contract["amount"] - fund_local) / len(temp_participants)

                    report_text = lang_manager.get_text("report_template", lang).format(
                        name=contract["name"],
                        amount=contract["amount"],
                        leader=contract["author_name"],
                        participants=participants_text,
                        fund=f"{fund_local:.2f}",
                        per_user=f"{per_user_local:.2f}"
                    )

                    await button_interaction.edit_original_response(content=report_text, view=self.view)

                except Exception:
                    await button_interaction.followup.send(lang_manager.get_text("participants_empty", lang), ephemeral=True)

        view = discord.ui.View()
        view.add_item(AddParticipantsButton())

        report_text = lang_manager.get_text("report_template", lang).format(
            name=contract["name"],
            amount=contract["amount"],
            leader=contract["author_name"],
            participants=participants,
            fund=f"{fund:.2f}",
            per_user=f"{per_user:.2f}"
        )

        await inter.response.edit_message(content=report_text, embed=None, view=view)

    view = ContractSelectView(contracts, lang, on_select)
    await interaction.response.send_message(lang_manager.get_text("select_contract", lang), view=view, ephemeral=True)

# --- Команда редактировать контракт ---
@bot.tree.command(name="editcontract", description="✏️ Редактировать контракт (только сумма и название)")
@app_commands.describe(name="Название контракта", amount="Новая сумма контракта")
async def edit_contract(interaction: discord.Interaction, name: str, amount: float):
    lang = db.get_user_language(interaction.user.id)
    contract = db.get_contract_by_name(name)
    if not contract:
        await interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return
    if contract["author_id"] != interaction.user.id:
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return
    if amount <= 0:
        await interaction.response.send_message(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
        return

    contract["amount"] = amount
    contract["timestamp"] = datetime.now(timezone.utc).isoformat()
    db.update_contract(contract)
    await interaction.response.send_message(lang_manager.get_text("contract_updated_success", lang).format(name=name, amount=amount))

# --- Команда удалить контракт ---
@bot.tree.command(name="deletecontract", description="❌ Удалить контракт")
@app_commands.describe(name="Название контракта")
async def delete_contract(interaction: discord.Interaction, name: str):
    lang = db.get_user_language(interaction.user.id)
    contract = db.get_contract_by_name(name)
    if not contract:
        await interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return
    # Проверка на администратора (или автора, по желанию)
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return
    db.delete_contract_by_name(name)
    await interaction.response.send_message(lang_manager.get_text("contract_deleted_success", lang).format(name=name))

# --- Команда итогового отчёта за N дней ---
@bot.tree.command(name="reportdays", description="📅 Итоговый отчёт по отправленным контрактам за N дней")
@app_commands.describe(days="Количество дней")
async def report_days(interaction: discord.Interaction, days: int):
    lang = db.get_user_language(interaction.user.id)
    reports = db.get_reports_by_days(days)
    if not reports:
        await interaction.response.send_message(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    total_amount = sum(r["amount"] for r in reports)
    fund_total = total_amount * Config.FUND_PERCENTAGE
    payout_total = total_amount - fund_total

    earnings = {}

    for r in reports:
        participants = r.get("participants") or []
        if not participants:
            participants = [f"@{r['author_name']}"]
        per_participant = 0
        if participants:
            per_participant = (r["amount"] * (1 - Config.FUND_PERCENTAGE)) / len(participants)
        for p in participants:
            earnings[p] = earnings.get(p, 0) + per_participant

    earnings_text = "\n".join(f"• {p}: {earn:.2f} USD" for p, earn in earnings.items()) if earnings else "-"

    message = lang_manager.get_text("report_days_summary", lang).format(
        days=days,
        total=f"{total_amount:.2f}",
        fund=f"{fund_total:.2f}",
        payout=f"{payout_total:.2f}",
        earnings=earnings_text,
    )

    await interaction.response.send_message(message)

# --- Команда информация о командах ---
@bot.tree.command(name="info", description="ℹ️ Информация о командах")
async def info(interaction: discord.Interaction):
    lang = db.get_user_language(interaction.user.id)
    text = (
        "📌 Доступные команды:\n"
        "/addcontract — ➕ Добавить контракт\n"
        "/editcontract — ✏️ Редактировать контракт (только автор может)\n"
        "/deletecontract — ❌ Удалить контракт (только админ)\n"
        "/report — 📄 Отчёт по контракту с кнопкой добавления участников\n"
        "/reportdays — 📅 Итоговый отчёт за N дней\n"
        "/language — 🌐 Сменить язык\n"
        "/info — ℹ️ Показать это сообщение\n"
    )
    await interaction.response.send_message(text, ephemeral=True)

# --- Запуск ---
if __name__ == "__main__":
    keep_alive()
    token = Config.DISCORD_BOT_TOKEN
    if not token:
        print("❌ DISCORD_BOT_TOKEN не установлен.")
        exit(1)
    bot.run(token)

