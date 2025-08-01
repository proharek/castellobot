import os
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
import threading
import asyncio

from core.database_supabase import (
    add_contract,
    get_contract_by_name,
    get_all_contracts,
    update_contract,
    delete_contract_by_name,
    set_user_language,
    get_user_language,
)
from core.language import Language

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)
tree = bot.tree

app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

async def get_lang(user_id: int) -> str:
    try:
        lang = await get_user_language(user_id)
        if lang not in ("ru", "ua"):
            return "ru"
        return lang
    except Exception as e:
        print(f"Ошибка получения языка: {e}")
        return "ru"

@tree.command(name="language", description="Сменить язык")
async def language(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    user_lang = await get_lang(interaction.user.id)
    lang_obj = Language(user_lang)

    class LangView(discord.ui.View):
        @discord.ui.button(label="Русский 🇷🇺", style=discord.ButtonStyle.primary)
        async def russian(self, interaction2: discord.Interaction, button: discord.ui.Button):
            await set_user_language(interaction2.user.id, "ru")
            await interaction2.response.edit_message(content="Язык установлен: Русский 🇷🇺", view=None)

        @discord.ui.button(label="Українська 🇺🇦", style=discord.ButtonStyle.primary)
        async def ukrainian(self, interaction2: discord.Interaction, button: discord.ui.Button):
            await set_user_language(interaction2.user.id, "ua")
            await interaction2.response.edit_message(content="Мова встановлена: Українська 🇺🇦", view=None)

    await interaction.followup.send(lang_obj.lang("select_language"), view=LangView(), ephemeral=True)

@tree.command(name="addcontract", description="Добавить контракт: /addcontract название сумма")
async def addcontract(interaction: discord.Interaction, *, args: str = None):
    await interaction.response.defer(ephemeral=True)
    lang = await get_lang(interaction.user.id)
    lang_obj = Language(lang)

    if not args:
        await interaction.followup.send(lang_obj.lang("error_no_args"), ephemeral=True)
        return

    parts = args.rsplit(" ", 1)
    if len(parts) != 2:
        await interaction.followup.send(lang_obj.lang("error_invalid_format"), ephemeral=True)
        return

    name, amount_str = parts[0].strip(), parts[1].strip()
    try:
        amount = float(amount_str.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except Exception:
        await interaction.followup.send(lang_obj.lang("invalid_amount"), ephemeral=True)
        return

    existing = await get_contract_by_name(name)
    if existing:
        await interaction.followup.send(lang_obj.lang("error_contract_exists"), ephemeral=True)
        return

    try:
        await add_contract(name, amount, interaction.user.id)
        await interaction.followup.send(lang_obj.lang("contract_added").format(name=name, amount=amount), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Ошибка добавления контракта: {e}", ephemeral=True)

@tree.command(name="contracts", description="Показать список контрактов")
async def contracts(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    lang = await get_lang(interaction.user.id)
    lang_obj = Language(lang)

    try:
        contracts = await get_all_contracts()
        if not contracts:
            await interaction.followup.send(lang_obj.lang("no_contracts_found"), ephemeral=True)
            return

        text = "\n".join(f"- {c['name']}: {c['amount']} USD" for c in contracts)
        await interaction.followup.send(f"Список контрактов:\n{text}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Ошибка получения контрактов: {e}", ephemeral=True)

@tree.command(name="editcontract", description="Редактировать контракт: /editcontract старое_название новое_название новая_сумма")
async def editcontract(interaction: discord.Interaction, old_name: str, new_name: str, new_amount: float):
    await interaction.response.defer(ephemeral=True)
    lang = await get_lang(interaction.user.id)
    lang_obj = Language(lang)

    contract = await get_contract_by_name(old_name)
    if not contract:
        await interaction.followup.send(lang_obj.lang("contract_not_found"), ephemeral=True)
        return

    if contract["author_id"] != interaction.user.id:
        await interaction.followup.send(lang_obj.lang("no_permission"), ephemeral=True)
        return

    if new_amount <= 0:
        await interaction.followup.send(lang_obj.lang("invalid_amount"), ephemeral=True)
        return

    try:
        await update_contract(old_name, new_name, new_amount)
        await interaction.followup.send(lang_obj.lang("contract_updated_success").format(name=new_name, amount=new_amount), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Ошибка обновления контракта: {e}", ephemeral=True)

@tree.command(name="deletecontract", description="Удалить контракт (только администратор)")
@commands.has_permissions(administrator=True)
async def deletecontract(interaction: discord.Interaction, *, name: str):
    await interaction.response.defer(ephemeral=True)
    lang = await get_lang(interaction.user.id)
    lang_obj = Language(lang)

    contract = await get_contract_by_name(name)
    if not contract:
        await interaction.followup.send(lang_obj.lang("contract_not_found"), ephemeral=True)
        return

    try:
        await delete_contract_by_name(name)
        await interaction.followup.send(lang_obj.lang("contract_deleted_success").format(name=name), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Ошибка удаления контракта: {e}", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Бот запущен: {bot.user} (ID: {bot.user.id})")
    await tree.sync()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
