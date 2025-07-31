import os
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta, timezone
import io
import asyncio

from core.database_supabase import DatabaseManager
from core.language import LanguageManager
from config import Config

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=Config.COMMAND_PREFIX, intents=intents)

db = DatabaseManager(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))
lang_manager = LanguageManager()

def is_admin(user: discord.User):
    admin_ids = Config.get_admin_user_ids()
    return user.id in admin_ids

def is_admin_or_role(member: discord.Member):
    if is_admin(member):
        return True
    admin_role_ids = Config.get_admin_role_ids()
    for role in member.roles:
        if role.id in admin_role_ids:
            return True
    return False

class LanguageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Русский", style=discord.ButtonStyle.secondary)
    async def set_ru(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.set_user_language(interaction.user.id, "ru")
        text = lang_manager.get_text("language_set_ru", "ru")
        if not interaction.response.is_done():
            await interaction.response.send_message(text, ephemeral=True)
        else:
            await interaction.followup.send(text, ephemeral=True)

    @discord.ui.button(label="Українська", style=discord.ButtonStyle.secondary, emoji="🇺🇦")
    async def set_ua(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.set_user_language(interaction.user.id, "ua")
        text = lang_manager.get_text("language_set_ua", "ua")
        if not interaction.response.is_done():
            await interaction.response.send_message(text, ephemeral=True)
        else:
            await interaction.followup.send(text, ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен.")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Синхронизировано {len(synced)} команд.")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")
@bot.tree.command(name="addcontract", description="➕ Добавить контракт")
@app_commands.describe(name="Название контракта", amount="Сумма контракта")
async def add_contract(interaction: discord.Interaction, name: str, amount: float):
    await interaction.response.defer(ephemeral=True)
    lang = await db.get_user_language(interaction.user.id)
    if amount <= 0:
        await interaction.followup.send(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
        return

    if len(name.strip()) == 0:
        await interaction.followup.send(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return

    contract = {
        "name": name.strip(),
        "amount": amount,
        "author_id": interaction.user.id,
        "author_name": interaction.user.display_name,
        "participants": [f"<@{interaction.user.id}>"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_archived": False
    }

    await db.add_contract(contract)
    await interaction.followup.send(
        lang_manager.get_text("contract_added", lang).format(name=contract["name"], amount=amount),
        ephemeral=True
    )

@bot.tree.command(name="language", description="🌐 Сменить язык")
async def language(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    lang = await db.get_user_language(interaction.user.id)
    view = LanguageView()
    embed = discord.Embed(
        title=lang_manager.get_text("select_language", lang),
        description="Русский\n🇺🇦 Українська",
        color=0x2b2d31
    )
    if not interaction.response.is_done():
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    else:
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="menu", description="📋 Главное меню")
async def menu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    lang = await db.get_user_language(interaction.user.id)
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
              "`/reportdays` — 📊 Отчёт за N дней\n"
              "`/reportlog` — 📜 Сохранённые отчёты\n"
              "`/backup` — 💾 Резервное копирование (админы)",
        inline=False
    )
    embed.add_field(
        name="⚙️ Система",
        value="`/menu` — Главное меню\n"
              "`/language` — Сменить язык",
        inline=False
    )
    await interaction.followup.send(embed=embed, ephemeral=True)
@bot.tree.command(name="report", description="📄 Отчёт по контракту")
async def report(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    lang = await db.get_user_language(interaction.user.id)
    contracts = await db.get_all_contracts()
    contracts = [c for c in contracts if not c.get("is_archived", False)]

    if not contracts:
        await interaction.followup.send(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    options = [
        discord.SelectOption(label=c["name"], description=f'{c["amount"]} USD') for c in contracts
    ]

    class ParticipantModal(discord.ui.Modal, title="✏️ Участники"):
        def __init__(self, contract):
            super().__init__(timeout=300)
            self.contract = contract
            self.input = discord.ui.TextInput(
                label="Участники (по одному в строке)",
                style=discord.TextStyle.paragraph,
                default="\n".join(contract.get("participants") or [f"<@{contract['author_id']}>"])
            )
            self.add_item(self.input)

        async def on_submit(self, modal_interaction: discord.Interaction):
            participants = [line.strip() for line in self.input.value.split("\n") if line.strip()]
            if not participants:
                participants = [f"<@{self.contract['author_id']}>"]

            self.contract["participants"] = participants
            await db.update_contract(self.contract)

            fund = self.contract["amount"] * Config.FUND_PERCENTAGE
            per_user = round((self.contract["amount"] - fund) / len(participants), 2)
            part_lines = "\n".join(f"• {p}" for p in participants)

            text = lang_manager.get_text("report_template", lang).format(
                amount=f"{self.contract['amount']:.2f}",
                leader=self.contract["author_name"],
                participants=part_lines,
                fund=f"{fund:.2f}",
                per_user=f"{per_user:.2f}"
            )

            await modal_interaction.followup.send(text, ephemeral=True)

    class ReportView(discord.ui.View):
        @discord.ui.select(placeholder="Выберите контракт", options=options)
        async def select_callback(self, interaction2: discord.Interaction, select: discord.ui.Select):
            selected = select.values[0]
            contract = await db.get_contract_by_name(selected)
            if not contract:
                await interaction2.followup.send(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
                return
            await interaction2.response.send_modal(ParticipantModal(contract))

    await interaction.followup.send(lang_manager.get_text("select_contract", lang), view=ReportView(), ephemeral=True)

@bot.tree.command(name="backup", description="💾 Экспорт всех данных")
async def backup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    lang = await db.get_user_language(interaction.user.id)

    if not is_admin_or_role(interaction.user):
        await interaction.followup.send(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    contracts = await db.get_all_contracts()
    reports = await db.get_all_reports()

    import json, io
    backup_data = {"contracts": contracts, "reports": reports}
    json_str = json.dumps(backup_data, indent=2, ensure_ascii=False)
    fp = io.StringIO(json_str)
    fp.seek(0)

    await interaction.followup.send("📦 Данные:", ephemeral=True)
    await interaction.followup.send(file=discord.File(fp, filename="backup.json"))

# --- Flask для UptimeRobot ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is alive!"

@app.route('/healthz')
def healthz():
    return "OK", 200

def run():
    app.run(host=Config.HOST, port=Config.PORT)

def keep_alive():
    Thread(target=run).start()

if __name__ == "__main__":
    keep_alive()

    token = Config.DISCORD_BOT_TOKEN
    if not token:
        print("❌ Переменная окружения DISCORD_BOT_TOKEN не задана.")
        exit(1)

    bot.run(token)

