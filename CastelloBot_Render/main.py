import discord
from discord.ext import commands
from discord import app_commands
import asyncio
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
from core.language import Language
from config import DISCORD_TOKEN

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)
tree = bot.tree

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

threading.Thread(target=run_flask).start()

async def get_user_lang(user_id: int) -> str:
    lang = await get_user_language(user_id)
    if lang not in ('ru', 'ua'):
        lang = 'ru'
    return lang

@tree.command(name="menu")
async def menu(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except (discord.errors.NotFound, discord.errors.InteractionResponded):
        pass

    lang = await get_user_lang(interaction.user.id)
    lang_obj = Language(lang)
    text = lang_obj.lang('menu_text')

    class MenuView(discord.ui.View):
        @discord.ui.button(label=lang_obj.lang('add_contract'), style=discord.ButtonStyle.green)
        async def add_contract_button(self, button: discord.ui.Button, interaction: discord.Interaction):
            await interaction.response.send_message(lang_obj.lang('use_command_addcontract'), ephemeral=True)

        @discord.ui.button(label=lang_obj.lang('contracts_report'), style=discord.ButtonStyle.primary)
        async def report_button(self, button: discord.ui.Button, interaction: discord.Interaction):
            await interaction.response.send_message(lang_obj.lang('use_command_report'), ephemeral=True)

    view = MenuView()
    await interaction.followup.send(text, view=view, ephemeral=True)

@tree.command(name="report")
async def report(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except (discord.errors.NotFound, discord.errors.InteractionResponded):
        pass

    try:
        contracts = await get_all_contracts()
        if not contracts:
            await interaction.followup.send("Контрактов нет.", ephemeral=True)
            return

        options = [
            discord.SelectOption(label=c['name'], description=f"{c['amount']} USD", value=c['name'])
            for c in contracts
        ]

        class ReportSelect(discord.ui.Select):
            def __init__(self):
                super().__init__(placeholder="Выберите контракт", min_values=1, max_values=1, options=options)

            async def callback(self, select_interaction: discord.Interaction):
                selected_name = self.values[0]
                contract = await get_contract_by_name(selected_name)
                if not contract:
                    await select_interaction.response.send_message("Контракт не найден.", ephemeral=True)
                    return

                total = contract['amount']
                author_id = contract['author_id']
                participants = contract.get('participants', [])
                if not participants:
                    participants = [author_id]

                guild = select_interaction.guild
                members = [guild.get_member(pid) for pid in participants] if guild else []
                members_mentions = [m.mention if m else f"User ID {pid}" for m, pid in zip(members, participants)]

                fund = total * 0.5
                share = (total - fund) / len(participants)

                report_text = (
                    f"💰 Сумма контракта: {total:.2f} USD\n"
                    f"👤 Старший группы: <@{author_id}>\n"
                    f"👥 Участники:\n" +
                    "\n".join(f"• {mention}" for mention in members_mentions) + "\n" +
                    f"🏦 В фонд семьи: {fund:.2f} USD (50%)\n"
                    f"💸 Каждому участнику: {share:.2f} USD"
                )
                await select_interaction.response.edit_message(content=report_text, view=None)

        view = discord.ui.View()
        view.add_item(ReportSelect())
        await interaction.followup.send("Выберите контракт для отчёта:", view=view, ephemeral=True)

    except Exception as e:
        try:
            await interaction.followup.send(f"Произошла ошибка: {e}", ephemeral=True)
        except Exception:
            print(f"Ошибка при отправке ошибки: {e}")

@tree.command(name="language")
async def language(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except (discord.errors.NotFound, discord.errors.InteractionResponded):
        pass

    lang = await get_user_lang(interaction.user.id)
    lang_obj = Language(lang)

    class LangView(discord.ui.View):
        @discord.ui.button(label="Русский 🇷🇺", style=discord.ButtonStyle.primary)
        async def ru_button(self, button: discord.ui.Button, interaction: discord.Interaction):
            await set_user_language(interaction.user.id, 'ru')
            await interaction.response.edit_message(content="Язык изменён на Русский 🇷🇺", view=None)

        @discord.ui.button(label="Українська 🇺🇦", style=discord.ButtonStyle.primary)
        async def ua_button(self, button: discord.ui.Button, interaction: discord.Interaction):
            await set_user_language(interaction.user.id, 'ua')
            await interaction.response.edit_message(content="Мову змінено на Українську 🇺🇦", view=None)

    await interaction.followup.send(lang_obj.lang('choose_language'), view=LangView(), ephemeral=True)

@tree.command(name="addcontract")
async def addcontract(interaction: discord.Interaction, *, args: str = None):
    try:
        await interaction.response.defer(ephemeral=True)
    except (discord.errors.NotFound, discord.errors.InteractionResponded):
        pass

    lang = await get_user_lang(interaction.user.id)
    lang_obj = Language(lang)

    if not args:
        await interaction.followup.send(lang_obj.lang('error_no_args'), ephemeral=True)
        return

    try:
        parts = args.rsplit(' ', maxsplit=1)
        if len(parts) != 2:
            await interaction.followup.send(lang_obj.lang('error_invalid_format'), ephemeral=True)
            return
        name = parts[0].strip()
        amount_str = parts[1].replace(',', '.').strip()
        amount = float(amount_str)
        if amount <= 0:
            await interaction.followup.send(lang_obj.lang('error_invalid_amount'), ephemeral=True)
            return
    except Exception:
        await interaction.followup.send(lang_obj.lang('error_invalid_amount'), ephemeral=True)
        return

    existing = await get_contract_by_name(name)
    if existing:
        await interaction.followup.send(lang_obj.lang('error_contract_exists'), ephemeral=True)
        return

    await add_contract(name=name, amount=amount, author_id=interaction.user.id)
    await interaction.followup.send(lang_obj.lang('contract_added').format(name=name, amount=amount), ephemeral=True)

@tree.command(name="editcontract")
async def editcontract(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except (discord.errors.NotFound, discord.errors.InteractionResponded):
        pass

    lang = await get_user_lang(interaction.user.id)
    lang_obj = Language(lang)

    contracts = await get_all_contracts()
    user_contracts = [c for c in contracts if c['author_id'] == interaction.user.id]
    if not user_contracts:
        await interaction.followup.send(lang_obj.lang('error_no_contracts'), ephemeral=True)
        return

    class EditSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=c['name'], description=f"{c['amount']} USD", value=c['name'])
                for c in user_contracts
            ]
            super().__init__(placeholder=lang_obj.lang('select_contract'), min_values=1, max_values=1, options=options)

        async def callback(self, select_interaction: discord.Interaction):
            selected_name = self.values[0]

            await select_interaction.response.send_message(lang_obj.lang('prompt_edit_new_name_amount'), ephemeral=True)

            def check(m):
                return m.author.id == interaction.user.id and m.channel == interaction.channel

            try:
                msg = await bot.wait_for('message', check=check, timeout=60)
                parts = msg.content.rsplit(' ', maxsplit=1)
                if len(parts) != 2:
                    await interaction.followup.send(lang_obj.lang('error_invalid_format'), ephemeral=True)
                    return
                new_name = parts[0].strip()
                new_amount_str = parts[1].replace(',', '.').strip()
                new_amount = float(new_amount_str)
                if new_amount <= 0:
                    await interaction.followup.send(lang_obj.lang('error_invalid_amount'), ephemeral=True)
                    return
            except asyncio.TimeoutError:
                await interaction.followup.send(lang_obj.lang('error_timeout'), ephemeral=True)
                return
            except Exception:
                await interaction.followup.send(lang_obj.lang('error_invalid_amount'), ephemeral=True)
                return

            contract = await get_contract_by_name(selected_name)
            if not contract:
                await interaction.followup.send(lang_obj.lang('error_contract_not_found'), ephemeral=True)
                return
            if contract['author_id'] != interaction.user.id:
                await interaction.followup.send(lang_obj.lang('error_no_permission'), ephemeral=True)
                return

            await update_contract(selected_name, new_name, new_amount)
            await interaction.followup.send(lang_obj.lang('contract_updated').format(name=new_name, amount=new_amount), ephemeral=True)

    view = discord.ui.View()
    view.add_item(EditSelect())
    await interaction.followup.send(lang_obj.lang('choose_contract_edit'), view=view, ephemeral=True)

@tree.command(name="deletecontract")
@commands.has_permissions(administrator=True)
async def deletecontract(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except (discord.errors.NotFound, discord.errors.InteractionResponded):
        pass

    lang = await get_user_lang(interaction.user.id)
    lang_obj = Language(lang)

    contracts = await get_all_contracts()
    if not contracts:
        await interaction.followup.send(lang_obj.lang('error_no_contracts'), ephemeral=True)
        return

    class DeleteSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=c['name'], description=f"{c['amount']} USD", value=c['name'])
                for c in contracts
            ]
            super().__init__(placeholder=lang_obj.lang('select_contract_delete'), min_values=1, max_values=1, options=options)

        async def callback(self, select_interaction: discord.Interaction):
            selected_name = self.values[0]
            await delete_contract_by_name(selected_name)
            await select_interaction.response.send_message(lang_obj.lang('contract_deleted').format(name=selected_name), ephemeral=True)

    view = discord.ui.View()
    view.add_item(DeleteSelect())
    await interaction.followup.send(lang_obj.lang('choose_contract_delete'), view=view, ephemeral=True)

@tree.command(name="info")
async def info(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except (discord.errors.NotFound, discord.errors.InteractionResponded):
        pass

    lang = await get_user_lang(interaction.user.id)
    lang_obj = Language(lang)

    text = lang_obj.lang('info_text')
    await interaction.followup.send(text, ephemeral=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.tree.sync()

bot.run(DISCORD_TOKEN)

