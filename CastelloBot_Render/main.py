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
    return any(role.id in admin_role_ids for role in member.roles)

class LanguageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Русский", style=discord.ButtonStyle.secondary)
    async def set_ru(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.set_user_language(interaction.user.id, "ru")
        await interaction.response.send_message(lang_manager.get_text("language_set_ru", "ru"), ephemeral=True)

    @discord.ui.button(label="Українська", style=discord.ButtonStyle.secondary, emoji="🇺🇦")
    async def set_ua(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.set_user_language(interaction.user.id, "ua")
        await interaction.response.send_message(lang_manager.get_text("language_set_ua", "ua"), ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен.")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Синхронизировано {len(synced)} команд.")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

@bot.tree.command(name="language", description="🌐 Сменить язык")
async def language(interaction: discord.Interaction):
    lang = await db.get_user_language(interaction.user.id)
    view = LanguageView()
    embed = discord.Embed(
        title=lang_manager.get_text("select_language", lang),
        description="Русский\n🇺🇦 Українська",
        color=0x2b2d31
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="menu", description="📋 Главное меню")
async def menu(interaction: discord.Interaction):
    lang = await db.get_user_language(interaction.user.id)
    embed = discord.Embed(
        title=lang_manager.get_text("menu_title", lang),
        description=lang_manager.get_text("menu_description", lang),
        color=0x2b2d31
    )
    embed.add_field(
        name="📂 Контракты",
        value=(
            "`/addcontract` — ➕ Добавить контракт\n"
            "`/editcontract` — ✏️ Редактировать контракт\n"
            "`/deletecontract` — ❌ Удалить контракт\n"
            "`/report` — 📄 Отчёт по контракту\n"
            "`/reportdays` — 📊 Отчёт за N дней\n"
            "`/reportlog` — 📜 Сохранённые отчёты\n"
            "`/backup` — 💾 Резервное копирование (админы)"
        ),
        inline=False
    )
    embed.add_field(
        name="⚙️ Система",
        value="`/menu` — Главное меню\n`/language` — Сменить язык",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
@bot.tree.command(name="addcontract", description="➕ Добавить контракт")
@app_commands.describe(name="Название контракта", amount="Сумма контракта")
async def add_contract(interaction: discord.Interaction, name: str, amount: float):
    lang = await db.get_user_language(interaction.user.id)
    if amount <= 0:
        await interaction.response.send_message(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
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
    await interaction.response.send_message(
        lang_manager.get_text("contract_added", lang).format(name=contract["name"], amount=amount)
    )

@bot.tree.command(name="editcontract", description="✏️ Редактировать контракт")
@app_commands.describe(name="Название контракта", amount="Новая сумма")
async def edit_contract(interaction: discord.Interaction, name: str, amount: float):
    lang = await db.get_user_language(interaction.user.id)
    contract = await db.get_contract_by_name(name)

    if not contract or contract.get("is_archived"):
        await interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return

    if contract["author_id"] != interaction.user.id:
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
        return

    contract["amount"] = amount
    await db.update_contract(contract)
    await interaction.response.send_message(
        lang_manager.get_text("contract_updated_success", lang).format(name=contract["name"], amount=amount)
    )

@bot.tree.command(name="deletecontract", description="❌ Удалить контракт")
@app_commands.describe(name="Название контракта")
async def delete_contract(interaction: discord.Interaction, name: str):
    lang = await db.get_user_language(interaction.user.id)
    contract = await db.get_contract_by_name(name)
    if not contract or contract.get("is_archived"):
        await interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return
    if contract["author_id"] != interaction.user.id and not is_admin_or_role(interaction.user):
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    await db.delete_contract_by_name(name)
    await interaction.response.send_message(
        lang_manager.get_text("contract_deleted_success", lang).format(name=name)
    )

@bot.tree.command(name="reportlog", description="📜 Сохранённые отчёты")
async def report_log(interaction: discord.Interaction):
    lang = await db.get_user_language(interaction.user.id)
    reports = await db.get_all_reports()
    if not reports:
        await interaction.response.send_message(lang_manager.get_text("no_reports_found", lang), ephemeral=True)
        return

    lines = []
    for r in reports[-10:]:
        time_str = r.get("timestamp", "")[:19].replace("T", " ")
        lines.append(f"**{r.get('contract_name')}** ({time_str})\nАвтор: <@{r.get('author_id')}>\n{r.get('message')}\n")

    await interaction.response.send_message("\n\n".join(lines), ephemeral=True)

@bot.tree.command(name="backup", description="💾 Резервная копия (только для админов)")
async def backup(interaction: discord.Interaction):
    if not is_admin_or_role(interaction.user):
        lang = await db.get_user_language(interaction.user.id)
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    contracts = await db.get_all_contracts()
    reports = await db.get_all_reports()
    import json
    data = {"contracts": contracts, "reports": reports}
    buffer = io.StringIO(json.dumps(data, indent=2, ensure_ascii=False))
    buffer.seek(0)
    await interaction.response.send_message("Резервная копия данных:", ephemeral=True)
    await interaction.followup.send(file=discord.File(buffer, "backup.json"))

# Flask-сервер для UptimeRobot и Cloudflare
app = Flask("")

@app.route("/")
def home():
    print("✅ Flask получил пинг от Cloudflare")
    return "Bot is alive!"

@app.route("/healthz")
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
        print("❌ DISCORD_BOT_TOKEN не установлен.")
        exit(1)
    bot.run(token)
