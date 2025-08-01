import os
import io
import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta, timezone

from core.database_supabase import DatabaseManager
from core.language import LanguageManager
from config import Config

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=Config.COMMAND_PREFIX, intents=intents)

db = DatabaseManager(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))
lang_manager = LanguageManager()

def is_admin(user: discord.User) -> bool:
    return user.id in Config.get_admin_user_ids()

def is_admin_or_role(member: discord.Member) -> bool:
    return is_admin(member) or any(role.id in Config.get_admin_role_ids() for role in member.roles)

# Flask сервер для пинга
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is alive!"

def run():
    app.run(host=Config.HOST, port=Config.PORT)

def keep_alive():
    Thread(target=run).start()

class LanguageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Русский", style=discord.ButtonStyle.secondary)
    async def set_ru(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.set_user_language(interaction.user.id, "ru")
        await safe_reply(interaction, lang_manager.get_text("language_set_ru", "ru"))

    @discord.ui.button(label="Українська", style=discord.ButtonStyle.secondary, emoji="🇺🇦")
    async def set_ua(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.set_user_language(interaction.user.id, "ua")
        await safe_reply(interaction, lang_manager.get_text("language_set_ua", "ua"))

async def safe_reply(interaction: discord.Interaction, message: str):
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(message, ephemeral=True)
        else:
            await interaction.followup.send(message, ephemeral=True)
    except discord.HTTPException:
        pass
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Бот {bot.user} запущен. Синхронизировано {len(synced)} команд.")
    except Exception as e:
        print(f"❌ Ошибка синхронизации: {e}")

@bot.tree.command(name="language", description="🌐 Сменить язык")
async def language(interaction: discord.Interaction):
    lang = await db.get_user_language(interaction.user.id)
    embed = discord.Embed(
        title=lang_manager.get_text("select_language", lang),
        description="🇷🇺 Русский\n🇺🇦 Українська",
        color=0x2b2d31
    )
    view = LanguageView()
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    except discord.HTTPException:
        pass

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
        value="`/addcontract`, `/editcontract`, `/deletecontract`\n"
              "`/report`, `/reportdays`, `/reportlog`, `/backup`",
        inline=False
    )
    embed.add_field(
        name="⚙️ Система",
        value="`/menu`, `/language`",
        inline=False
    )
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)
    except discord.HTTPException:
        pass

@bot.tree.command(name="addcontract", description="➕ Добавить контракт")
@app_commands.describe(name="Название контракта", amount="Сумма в USD")
async def addcontract(interaction: discord.Interaction, name: str, amount: float):
    lang = await db.get_user_language(interaction.user.id)
    if amount <= 0:
        await safe_reply(interaction, lang_manager.get_text("invalid_amount", lang))
        return

    await db.add_contract(name=name, amount=amount, author_id=interaction.user.id)
    await safe_reply(interaction, lang_manager.get_text("contract_added", lang).format(name=name, amount=amount))
# ----------------- Команда: /report -----------------
@bot.tree.command(name="report", description="📄 Отчёт по контракту")
async def report(interaction: discord.Interaction):
    lang = await db.get_user_language(interaction.user.id)
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        else:
            await interaction.followup.defer(ephemeral=True)
    except discord.HTTPException:
        pass

    contracts = await db.get_all_contracts()
    if not contracts:
        await interaction.followup.send(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    class ContractSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=c["name"], value=c["name"]) for c in contracts
            ]
            super().__init__(placeholder=lang_manager.get_text("select_contract", lang), min_values=1, max_values=1, options=options)

        async def callback(self, select_interaction: discord.Interaction):
            selected = self.values[0]
            contract = await db.get_contract_by_name(selected)
            if not contract:
                await select_interaction.response.send_message(
                    lang_manager.get_text("contract_not_found", lang), ephemeral=True
                )
                return

            participants = contract.get("participants", []) or []
            if not participants:
                participants = [contract["author_id"]]

            fund = round(contract["amount"] * 0.5, 2)
            per_user = round((contract["amount"] - fund) / len(participants), 2)
            formatted_users = "\n".join([f"• <@{uid}>" for uid in participants])

            text = lang_manager.get_text("report_template", lang).format(
                amount=contract["amount"],
                leader=contract["author_id"],
                participants=formatted_users,
                fund=f"{fund:.2f}",
                per_user=f"{per_user:.2f}"
            )

            await select_interaction.response.send_message(text, ephemeral=True)

    view = discord.ui.View(timeout=120)
    view.add_item(ContractSelect())

    await interaction.followup.send(view=view, ephemeral=True)
# ----------------- Команда: /reportdays -----------------
@bot.tree.command(name="reportdays", description="📊 Отчёт за N дней")
@app_commands.describe(days="Количество дней")
async def reportdays(interaction: discord.Interaction, days: int):
    lang = await db.get_user_language(interaction.user.id)

    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        else:
            await interaction.followup.defer(ephemeral=True)
    except discord.HTTPException:
        pass

    contracts = await db.get_all_contracts()
    now = datetime.now(timezone.utc)
    filtered = [c for c in contracts if "timestamp" in c and datetime.fromisoformat(c["timestamp"]) > now - timedelta(days=days)]

    if not filtered:
        await interaction.followup.send(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    total_amount = 0
    user_earnings = {}

    for c in filtered:
        participants = c.get("participants", []) or [c["author_id"]]
        fund = round(c["amount"] * 0.5, 2)
        per_user = round((c["amount"] - fund) / len(participants), 2)
        total_amount += c["amount"]

        for uid in participants:
            user_earnings[uid] = user_earnings.get(uid, 0) + per_user

    lines = [f"💰 Общая сумма: {total_amount:.2f} USD\n"]
    for uid, earned in user_earnings.items():
        lines.append(f"<@{uid}> — {earned:.2f} USD")

    await interaction.followup.send("\n".join(lines), ephemeral=True)

# ----------------- Команда: /editcontract -----------------
@bot.tree.command(name="editcontract", description="✏️ Редактировать контракт (название и сумма)")
async def editcontract(interaction: discord.Interaction):
    lang = await db.get_user_language(interaction.user.id)

    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        else:
            await interaction.followup.defer(ephemeral=True)
    except discord.HTTPException:
        pass

    contracts = await db.get_all_contracts()
    user_contracts = [c for c in contracts if c["author_id"] == interaction.user.id]

    if not user_contracts:
        await interaction.followup.send(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    class ContractEdit(discord.ui.Select):
        def __init__(self):
            options = [discord.SelectOption(label=c["name"], value=c["name"]) for c in user_contracts]
            super().__init__(placeholder="Выбери контракт для редактирования", options=options)

        async def callback(self, select_interaction: discord.Interaction):
            selected_name = self.values[0]
            contract = await db.get_contract_by_name(selected_name)

            modal = discord.ui.Modal(title="Редактирование контракта")

            name_input = discord.ui.TextInput(label="Новое название", default=contract["name"], required=True)
            amount_input = discord.ui.TextInput(label="Новая сумма (USD)", default=str(contract["amount"]), required=True)

            modal.add_item(name_input)
            modal.add_item(amount_input)

            async def on_submit(interaction_modal: discord.Interaction):
                try:
                    new_amount = float(amount_input.value)
                    if new_amount <= 0:
                        await interaction_modal.response.send_message(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
                        return
                except ValueError:
                    await interaction_modal.response.send_message(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
                    return

                await db.update_contract(selected_name, name_input.value, new_amount)
                text = lang_manager.get_text("contract_updated_success", lang).format(name=name_input.value, amount=new_amount)
                await interaction_modal.response.send_message(text, ephemeral=True)

            modal.on_submit = on_submit
            await select_interaction.response.send_modal(modal)

    view = discord.ui.View(timeout=180)
    view.add_item(ContractEdit())
    await interaction.followup.send(view=view, ephemeral=True)
# ----------------- Команда: /deletecontract -----------------
@bot.tree.command(name="deletecontract", description="❌ Удалить контракт (только для администратора)")
async def deletecontract(interaction: discord.Interaction):
    lang = await db.get_user_language(interaction.user.id)

    if not is_admin(interaction.user):
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    contracts = await db.get_all_contracts()
    if not contracts:
        await interaction.response.send_message(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    class DeleteSelect(discord.ui.Select):
        def __init__(self):
            options = [discord.SelectOption(label=c["name"], value=c["name"]) for c in contracts]
            super().__init__(placeholder="Выбери контракт для удаления", options=options)

        async def callback(self, select_interaction: discord.Interaction):
            selected_name = self.values[0]
            await db.delete_contract_by_name(selected_name)
            text = lang_manager.get_text("contract_deleted_success", lang).format(name=selected_name)
            await select_interaction.response.send_message(text, ephemeral=True)

    view = discord.ui.View(timeout=60)
    view.add_item(DeleteSelect())
    await interaction.response.send_message(view=view, ephemeral=True)
