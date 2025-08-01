import discord
from discord.ext import commands
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
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

threading.Thread(target=run_flask).start()

# ------------------- Языковая поддержка -------------------

async def get_user_lang(user_id: int) -> str:
    lang = await get_user_language(user_id)
    if lang not in ('ru', 'ua'):
        lang = 'ru'  # язык по умолчанию
    return lang

# ------------------- Команды -------------------

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command(name='language')
async def language(ctx: commands.Context):
    lang = await get_user_lang(ctx.author.id)
    lang_obj = Language(lang)

    # Кнопки смены языка
    class LangView(discord.ui.View):
        @discord.ui.button(label="Русский 🇷🇺", style=discord.ButtonStyle.primary)
        async def ru_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await set_user_language(interaction.user.id, 'ru')
            await interaction.response.edit_message(content="Язык изменён на Русский 🇷🇺", view=None)

        @discord.ui.button(label="Українська 🇺🇦", style=discord.ButtonStyle.primary)
        async def ua_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await set_user_language(interaction.user.id, 'ua')
            await interaction.response.edit_message(content="Мову змінено на Українську 🇺🇦", view=None)

    await ctx.send(lang_obj.lang('choose_language'), view=LangView())

@bot.command(name='menu')
async def menu(ctx: commands.Context):
    lang = await get_user_lang(ctx.author.id)
    lang_obj = Language(lang)
    text = lang_obj.lang('menu_text')

    class MenuView(discord.ui.View):
        @discord.ui.button(label=lang_obj.lang('add_contract'), style=discord.ButtonStyle.green)
        async def add_contract_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(lang_obj.lang('use_command_addcontract'), ephemeral=True)

        @discord.ui.button(label=lang_obj.lang('contracts_report'), style=discord.ButtonStyle.primary)
        async def report_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(lang_obj.lang('use_command_report'), ephemeral=True)

    await ctx.send(text, view=MenuView())

@bot.command(name='addcontract')
async def addcontract(ctx: commands.Context, *, args=None):
    lang = await get_user_lang(ctx.author.id)
    lang_obj = Language(lang)

    if not args:
        await ctx.send(lang_obj.lang('error_no_args'))
        return

    try:
        # Ожидаем формат: название сумма
        parts = args.rsplit(' ', maxsplit=1)
        if len(parts) != 2:
            await ctx.send(lang_obj.lang('error_invalid_format'))
            return
        name = parts[0].strip()
        amount_str = parts[1].replace(',', '.').strip()
        amount = float(amount_str)
        if amount <= 0:
            await ctx.send(lang_obj.lang('error_invalid_amount'))
            return
    except Exception:
        await ctx.send(lang_obj.lang('error_invalid_amount'))
        return

    existing = await get_contract_by_name(name)
    if existing:
        await ctx.send(lang_obj.lang('error_contract_exists'))
        return

    await add_contract(name=name, amount=amount, author_id=ctx.author.id)
    await ctx.send(lang_obj.lang('contract_added').format(name=name, amount=amount))

@bot.command(name='editcontract')
async def editcontract(ctx: commands.Context):
    lang = await get_user_lang(ctx.author.id)
    lang_obj = Language(lang)

    contracts = await get_all_contracts()
    user_contracts = [c for c in contracts if c['author_id'] == ctx.author.id]
    if not user_contracts:
        await ctx.send(lang_obj.lang('error_no_contracts'))
        return

    class EditSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=c['name'], description=f"{c['amount']} USD", value=c['name'])
                for c in user_contracts
            ]
            super().__init__(placeholder=lang_obj.lang('select_contract'), min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            selected_name = self.values[0]

            await interaction.response.send_message(
                lang_obj.lang('prompt_edit_new_name_amount'),
                ephemeral=True
            )

            def check(m):
                return m.author.id == ctx.author.id and m.channel == ctx.channel

            try:
                msg = await bot.wait_for('message', check=check, timeout=60)
                parts = msg.content.rsplit(' ', maxsplit=1)
                if len(parts) != 2:
                    await ctx.send(lang_obj.lang('error_invalid_format'))
                    return
                new_name = parts[0].strip()
                new_amount_str = parts[1].replace(',', '.').strip()
                new_amount = float(new_amount_str)
                if new_amount <= 0:
                    await ctx.send(lang_obj.lang('error_invalid_amount'))
                    return
            except asyncio.TimeoutError:
                await ctx.send(lang_obj.lang('error_timeout'))
                return
            except Exception:
                await ctx.send(lang_obj.lang('error_invalid_amount'))
                return

            contract = await get_contract_by_name(selected_name)
            if not contract:
                await ctx.send(lang_obj.lang('error_contract_not_found'))
                return
            if contract['author_id'] != ctx.author.id:
                await ctx.send(lang_obj.lang('error_no_permission'))
                return

            await update_contract(selected_name, new_name, new_amount)
            await ctx.send(lang_obj.lang('contract_updated').format(name=new_name, amount=new_amount))

    view = discord.ui.View()
    view.add_item(EditSelect())
    await ctx.send(lang_obj.lang('choose_contract_edit'), view=view)

@bot.command(name='deletecontract')
@commands.has_permissions(administrator=True)
async def deletecontract(ctx: commands.Context):
    lang = await get_user_lang(ctx.author.id)
    lang_obj = Language(lang)

    contracts = await get_all_contracts()
    if not contracts:
        await ctx.send(lang_obj.lang('error_no_contracts'))
        return

    class DeleteSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=c['name'], description=f"{c['amount']} USD", value=c['name'])
                for c in contracts
            ]
            super().__init__(placeholder=lang_obj.lang('select_contract_delete'), min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            selected_name = self.values[0]
            await delete_contract_by_name(selected_name)
            await interaction.response.send_message(lang_obj.lang('contract_deleted').format(name=selected_name), ephemeral=True)

    view = discord.ui.View()
    view.add_item(DeleteSelect())
    await ctx.send(lang_obj.lang('choose_contract_delete'), view=view)

@bot.command(name='report')
async def report(ctx: commands.Context):
    lang = await get_user_lang(ctx.author.id)
    lang_obj = Language(lang)

    contracts = await get_all_contracts()
    if not contracts:
        await ctx.send(lang_obj.lang('error_no_contracts'))
        return

    class ReportSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=c['name'], description=f"{c['amount']} USD", value=c['name'])
                for c in contracts
            ]
            super().__init__(placeholder=lang_obj.lang('select_contract_report'), min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            selected_name = self.values[0]
            contract = await get_contract_by_name(selected_name)
            if not contract:
                await interaction.response.send_message(lang_obj.lang('error_contract_not_found'), ephemeral=True)
                return

            # Формируем отчёт
            total = contract['amount']
            author_id = contract['author_id']

            # Допустим, в контракте есть список участников, если нет — используем только автора
            participants = contract.get('participants', [])
            if not participants:
                participants = [author_id]

            # Берём пользователя из дискорда по id
            guild = ctx.guild
            members = [guild.get_member(pid) for pid in participants]
            members_mentions = [m.mention if m else f"User ID {pid}" for m, pid in zip(members, participants)]

            fund = total * 0.5
            share = (total - fund) / len(participants)

            report_text = (
                f"💰 {lang_obj.lang('contract_amount')}: {total:.2f} USD\n"
                f"👤 {lang_obj.lang('group_leader')}: <@{author_id}>\n"
                f"👥 {lang_obj.lang('participants')}:\n" +
                "\n".join(f"• {mention}" for mention in members_mentions) + "\n" +
                f"🏦 {lang_obj.lang('family_fund')}: {fund:.2f} USD (50%)\n"
                f"💸 {lang_obj.lang('each_participant')}: {share:.2f} USD"
            )

            await interaction.response.send_message(report_text, ephemeral=True)

    view = discord.ui.View()
    view.add_item(ReportSelect())
    await ctx.send(lang_obj.lang('choose_contract_report'), view=view)

@bot.command(name='info')
async def info(ctx: commands.Context):
    lang = await get_user_lang(ctx.author.id)
    lang_obj = Language(lang)

    text = lang_obj.lang('info_text')
    await ctx.send(text)

# Запуск бота
bot.run(DISCORD_TOKEN)
