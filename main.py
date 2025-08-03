
import os
import json
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

bot = commands.Bot(intents=intents)
db = DatabaseManager()
lang_manager = LanguageManager()

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
            msg = await bot.wait_for('message', check=check, timeout=60)
            mentions = msg.mentions

            await msg.delete()  # Удалить сообщение с тегами

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

            text = lang_manager.get_text("report_template", self.lang).format(
                name=contract["name"],
                amount=contract["amount"],
                leader=contract["author_name"],
                participants=participants_text,
                fund=f"{fund:.2f}",
                per_user=f"{per_user:.2f}"
            )

            await interaction.channel.send(text)

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

@bot.tree.command(name="language", description="🌐 Сменить язык")
@app_commands.choices(language=[
    app_commands.Choice(name="RU", value="ru"),
    app_commands.Choice(name="UA", value="ua"),
])
async def change_language(interaction: discord.Interaction, language: app_commands.Choice[str]):
    db.set_user_language(interaction.user.id, language.value)
    await interaction.response.send_message(
        lang_manager.get_text(f"language_set_{language.value}", language.value),
        ephemeral=True
    )

@bot.tree.command(name="reportdays", description="📅 Отчёт за последние дни")
@app_commands.describe(days="Количество дней (макс. 30)")
async def report_days(interaction: discord.Interaction, days: int = Config.DEFAULT_REPORT_DAYS):
    lang = db.get_user_language(interaction.user.id)
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

@bot.tree.command(name="info", description="ℹ️ Информация о командах")
async def info(interaction: discord.Interaction):
    lang = db.get_user_language(interaction.user.id)
    await interaction.response.send_message(
        "📌 Команды:
"
        "/language — сменить язык (RU / UA)
"
        "/addcontract — добавить контракт
"
        "/editcontract — редактировать контракт (только автор)
"
        "/deletecontract — удалить контракт (только админ)
"
        "/report — выбрать контракт и сформировать отчёт
"
        "/reportdays — отчёт по дням
"
        "/info — справка

"
        "В /report есть кнопка ➕ Добавить участников (временные). Отчёт сохраняется автоматически.",
        ephemeral=True
    )

keep_alive()
bot.run(Config.DISCORD_BOT_TOKEN)
