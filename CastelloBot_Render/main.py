import os
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta, timezone

from core.database import DatabaseManager
from core.language import LanguageManager
from config import Config

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=Config.COMMAND_PREFIX, intents=intents)

db = DatabaseManager()
lang_manager = LanguageManager()

class LanguageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Русский", style=discord.ButtonStyle.secondary)
    async def set_ru(self, interaction: discord.Interaction, button: discord.ui.Button):
        db.set_user_language(interaction.user.id, "ru")
        if not interaction.response.is_done():
            await interaction.response.send_message(lang_manager.get_text("language_set_ru", "ru"), ephemeral=True)

    @discord.ui.button(label="Українська", style=discord.ButtonStyle.secondary, emoji="🇺🇦")
    async def set_ua(self, interaction: discord.Interaction, button: discord.ui.Button):
        db.set_user_language(interaction.user.id, "ua")
        if not interaction.response.is_done():
            await interaction.response.send_message(lang_manager.get_text("language_set_ua", "ua"), ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен.")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Синхронизировано {len(synced)} команд.")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

# --- Команды бота ---
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
    await interaction.response.send_message(
        lang_manager.get_text("contract_added", lang).format(name=name, amount=amount)
    )

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

    contract["amount"] = amount
    db.update_contract(contract)

    await interaction.response.send_message(
        lang_manager.get_text("contract_updated_success", lang).format(name=name, amount=amount)
    )

@bot.tree.command(name="deletecontract", description="❌ Удалить контракт")
@app_commands.describe(name="Название контракта")
async def delete_contract(interaction: discord.Interaction, name: str):
    lang = db.get_user_language(interaction.user.id)
    contract = db.get_contract_by_name(name)

    if not contract:
        await interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return

    if contract.get("author_id") != interaction.user.id:
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    db.delete_contract_by_name(name)
    await interaction.response.send_message(
        lang_manager.get_text("contract_deleted_success", lang).format(name=name)
    )

@bot.tree.command(name="report", description="📄 Отчёт по контракту")
async def report(interaction: discord.Interaction):
    lang = db.get_user_language(interaction.user.id)
    contracts = db.get_all_contracts()

    if not contracts:
        await interaction.response.send_message(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    options = [
        discord.SelectOption(label=c["name"], description=f'{c["amount"]} USD')
        for c in contracts
    ]

    class ParticipantModal(discord.ui.Modal, title="✏️ Изменить участников"):
        def __init__(self, contract):
            super().__init__(timeout=300)
            self.contract = contract
            self.input = discord.ui.TextInput(
                label="Участники (по одному в строке)",
                style=discord.TextStyle.paragraph,
                default="\n".join(contract.get("participants", []) or [contract["author_name"]])
            )
            self.add_item(self.input)

        async def on_submit(self, modal_interaction: discord.Interaction):
            participants = [line.strip() for line in self.input.value.split("\n") if line.strip()]
            if not participants:
                participants = [self.contract["author_name"]]
            self.contract["participants"] = participants
            db.update_contract(self.contract)

            fund = self.contract["amount"] * Config.FUND_PERCENTAGE
            per_user = round((self.contract["amount"] - fund) / len(participants), 2)
            lines = "\n".join(f"• @{p}" for p in participants)

            report_text = lang_manager.get_text("report_template", lang).format(
                name=self.contract["name"],
                amount=f"{self.contract['amount']:,.2f}",
                leader=self.contract["author_name"],
                participants=lines,
                fund=f"{fund:,.2f}",
                per_user=f"{per_user:,.2f}"
            )

            if not modal_interaction.response.is_done():
                await modal_interaction.response.send_message(report_text)
            else:
                await modal_interaction.followup.send(report_text)

    class ReportView(discord.ui.View):
        @discord.ui.select(
            placeholder="Выберите контракт",
            options=options,
            min_values=1,
            max_values=1
        )
        async def select(self, select_interaction: discord.Interaction, select: discord.ui.Select):
            selected = select.values[0]
            contract = db.get_contract_by_name(selected)
            if not contract:
                if not select_interaction.response.is_done():
                    await select_interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
                else:
                    await select_interaction.followup.send(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
                return

            await select_interaction.response.send_modal(ParticipantModal(contract))

    await interaction.response.send_message(lang_manager.get_text("select_contract", lang), view=ReportView(), ephemeral=True)

@bot.tree.command(name="reportdays", description="📊 Отчёт за N дней")
@app_commands.describe(days="Сколько дней учитывать")
async def report_days(interaction: discord.Interaction, days: int):
    lang = db.get_user_language(interaction.user.id)
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(days=days)
    contracts = db.get_all_contracts()

    recent = []
    for c in contracts:
        try:
            c_time = datetime.fromisoformat(c.get("timestamp", "2000-01-01T00:00:00+00:00"))
            if c_time >= threshold:
                recent.append(c)
        except Exception:
            continue

    if not recent:
        await interaction.response.send_message(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    total = sum(c["amount"] for c in recent)
    fund = total * Config.FUND_PERCENTAGE
    user_totals = {}

    for contract in recent:
        amount = contract["amount"]
        participants = contract.get("participants", []) or [contract["author_name"]]
        per = round((amount - amount * Config.FUND_PERCENTAGE) / len(participants), 2)
        for p in participants:
            user_totals[p] = user_totals.get(p, 0) + per

    lines = [f"📊 Отчёт за последние {days} дней:",
             f"💰 Общая сумма контрактов: {total:,.0f} USD",
             f"🏦 В фонд семьи: {fund:,.0f} USD (50%)",
             f"💸 Выплачено участникам всего: {total - fund:,.0f} USD",
             f"👥 Доход по участникам:"]
    for user, earned in sorted(user_totals.items(), key=lambda x: -x[1]):
        lines.append(f"• @{user} — {earned:,.0f} USD")

    await interaction.response.send_message("\n".join(lines))

@bot.tree.command(name="language", description="🌐 Сменить язык")
async def language(interaction: discord.Interaction):
    lang = db.get_user_language(interaction.user.id)
    view = LanguageView()
    embed = discord.Embed(
        title=lang_manager.get_text("select_language", lang),
        description="Русский\n🇺🇦 Українська",
        color=0x2b2d31
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="menu", description="📋 Главное меню")
async def menu(interaction: discord.Interaction):
    lang = db.get_user_language(interaction.user.id)
    embed = discord.Embed(
        title=lang_manager.get_text("menu_title", lang),
        description=lang_manager.get_text("menu_description", lang),
        color=0x2b2d31
    )
    embed.add_field(
        name="📂 Контракты",
        value="`/addcontract` — ➕ Добавить контракт\n"
              "`/editcontract` — ✏️ Редактировать контракт\n"
              "`/deletecontract` — ❌ Удалить контракт\n"
              "`/report` — 📄 Отчёт по контракту\n"
              "`/reportdays` — 📊 Отчёт за N дней",
        inline=False
    )
    embed.add_field(
        name="⚙️ Система",
        value="`/menu` — Главное меню\n"
              "`/language` — Сменить язык",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Flask для UptimeRobot и Cloudflare ---

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    print("✅ Flask получил пинг от Cloudflare")
    return "Bot is alive!"

@app.route('/healthz')
def healthz():
    return "OK", 200

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# --- Запуск бота и Flask параллельно ---

if __name__ == "__main__":
    keep_alive()

    token = Config.DISCORD_BOT_TOKEN
    if not token:
        print("❌ DISCORD_BOT_TOKEN не установлен.")
        exit(1)

    bot.run(token)
