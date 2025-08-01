import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
import threading
import os

from core.database_supabase import (
    add_contract,
    get_contract_by_name,
    get_all_contracts,
    update_contract,
    delete_contract_by_name,
    set_user_language,
    get_user_language,
    save_report,
    get_all_reports
)
from core.language import LanguageManager
from config import DISCORD_TOKEN

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

lang_manager = LanguageManager()

app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is running!'

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

threading.Thread(target=run_flask).start()

async def get_lang(user_id: int) -> str:
    lang = await get_user_language(user_id)
    return lang if lang in ['ru', 'ua'] else 'ru'

@tree.command(name="language", description="Сменить язык")
async def language(interaction: discord.Interaction):
    lang = await get_lang(interaction.user.id)
    await interaction.response.defer(ephemeral=True)

    class LangView(discord.ui.View):
        @discord.ui.button(label="Русский 🇷🇺", style=discord.ButtonStyle.primary)
        async def ru(self, button, i: discord.Interaction):
            await set_user_language(i.user.id, "ru")
            await i.response.edit_message(content=lang_manager.get_text("language_set_ru", "ru"), view=None)

        @discord.ui.button(label="Українська 🇺🇦", style=discord.ButtonStyle.primary)
        async def ua(self, button, i: discord.Interaction):
            await set_user_language(i.user.id, "ua")
            await i.response.edit_message(content=lang_manager.get_text("language_set_ua", "ua"), view=None)

    await interaction.followup.send(lang_manager.get_text("select_language", lang), view=LangView(), ephemeral=True)

@tree.command(name="menu", description="📋 Главное меню")
async def menu(interaction: discord.Interaction):
    lang = await get_lang(interaction.user.id)
    await interaction.response.defer(ephemeral=True)

    class MenuView(discord.ui.View):
        @discord.ui.button(label="➕ Добавить контракт", style=discord.ButtonStyle.success)
        async def add(self, button, i: discord.Interaction):
            await i.response.send_message("/addcontract Название 1000", ephemeral=True)

        @discord.ui.button(label="📄 Отчёт о контрактах", style=discord.ButtonStyle.primary)
        async def report(self, button, i: discord.Interaction):
            await i.response.send_message("/report", ephemeral=True)

    await interaction.followup.send(
        f"**{lang_manager.get_text('menu_title', lang)}**\n{lang_manager.get_text('menu_description', lang)}",
        view=MenuView(),
        ephemeral=True
    )

@tree.command(name="addcontract", description="➕ Добавить контракт")
@app_commands.describe(args="Формат: Название 1000")
async def addcontract(interaction: discord.Interaction, args: str):
    lang = await get_lang(interaction.user.id)
    await interaction.response.defer(ephemeral=True)

    try:
        parts = args.rsplit(" ", maxsplit=1)
        if len(parts) != 2:
            await interaction.followup.send(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
            return
        name, amount_str = parts
        amount = float(amount_str.replace(",", "."))
        if amount <= 0:
            await interaction.followup.send(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
            return
    except Exception:
        await interaction.followup.send(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
        return

    existing = await get_contract_by_name(name.strip())
    if existing:
        await interaction.followup.send("❌ Контракт с таким названием уже существует.", ephemeral=True)
        return

    await add_contract(name=name.strip(), amount=amount, author_id=interaction.user.id)
    await interaction.followup.send(
        lang_manager.get_text("contract_added", lang).format(name=name, amount=amount),
        ephemeral=True
    )

@tree.command(name="report", description="📄 Отчёт о контрактах")
async def report(interaction: discord.Interaction):
    lang = await get_lang(interaction.user.id)
    await interaction.response.defer(ephemeral=True)

    contracts = await get_all_contracts()
    if not contracts:
        await interaction.followup.send(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    options = [
        discord.SelectOption(label=c['name'], description=f"{c['amount']} USD", value=c['name'])
        for c in contracts
    ]

    class SelectContract(discord.ui.Select):
        def __init__(self):
            super().__init__(placeholder=lang_manager.get_text("select_contract", lang),
                             min_values=1, max_values=1, options=options)

        async def callback(self, select_interaction: discord.Interaction):
            selected = self.values[0]
            contract = await get_contract_by_name(selected)
            if not contract:
                await select_interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
                return

            total = contract['amount']
            leader_id = contract['author_id']
            participants = contract.get('participants', []) or [leader_id]

            guild = interaction.guild
            members = [guild.get_member(pid) for pid in participants]
            mention_list = [m.mention if m else f"<@{pid}>" for m, pid in zip(members, participants)]

            fund = total * 0.5
            per_user = (total - fund) / len(participants)

            report = lang_manager.get_text("report_template", lang).format(
                amount=f"{total:.2f}",
                leader=guild.get_member(leader_id).name if guild else f"{leader_id}",
                participants="\n".join(f"• {m}" for m in mention_list),
                fund=f"{fund:.2f}",
                per_user=f"{per_user:.2f}"
            )

            await select_interaction.response.edit_message(content=report, view=None)

    view = discord.ui.View()
    view.add_item(SelectContract())
    await interaction.followup.send(lang_manager.get_text("select_contract", lang), view=view, ephemeral=True)

@tree.command(name="deletecontract", description="❌ Удалить контракт (только для админа)")
@app_commands.describe(name="Название контракта")
async def deletecontract(interaction: discord.Interaction, name: str):
    lang = await get_lang(interaction.user.id)
    await interaction.response.defer(ephemeral=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    contract = await get_contract_by_name(name)
    if not contract:
        await interaction.followup.send(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return

    await delete_contract_by_name(name)
    await interaction.followup.send(lang_manager.get_text("contract_deleted_success", lang).format(name=name), ephemeral=True)

@tree.command(name="info", description="ℹ️ Информация о командах")
async def info(interaction: discord.Interaction):
    lang = await get_lang(interaction.user.id)
    await interaction.response.defer(ephemeral=True)

    text = (
        "**Доступные команды:**\n"
        "/menu — Главное меню\n"
        "/addcontract Название 1000 — добавить контракт\n"
        "/report — сформировать отчёт\n"
        "/deletecontract Название — удалить контракт (админ)\n"
        "/language — сменить язык\n"
        "/info — показать это сообщение"
    )
    await interaction.followup.send(text, ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await tree.sync()
        print(f"🔧 Synced {len(synced)} команд")
    except Exception as e:
        print(f"Ошибка при синхронизации команд: {e}")

bot.run(DISCORD_TOKEN)

