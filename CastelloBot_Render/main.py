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
        if not interaction.response.is_done():
            await interaction.response.send_message(lang_manager.get_text("language_set_ru", "ru"), ephemeral=True)

    @discord.ui.button(label="Українська", style=discord.ButtonStyle.secondary, emoji="🇺🇦")
    async def set_ua(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.set_user_language(interaction.user.id, "ua")
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

@bot.tree.command(name="addcontract", description="➕ Добавить контракт")
@app_commands.describe(name="Название контракта", amount="Сумма контракта")
async def add_contract(interaction: discord.Interaction, name: str, amount: float):
    await interaction.response.defer(ephemeral=True)  # Отложенный ответ
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

@bot.tree.command(name="editcontract", description="✏️ Редактировать контракт")
@app_commands.describe(name="Название контракта", amount="Новая сумма")
async def edit_contract(interaction: discord.Interaction, name: str, amount: float):
    await interaction.response.defer(ephemeral=True)
    lang = await db.get_user_language(interaction.user.id)
    contract = await db.get_contract_by_name(name)

    if not contract or contract.get("is_archived", False):
        await interaction.followup.send(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return

    if contract.get("author_id") != interaction.user.id:
        await interaction.followup.send(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    if amount <= 0:
        await interaction.followup.send(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
        return

    contract["amount"] = amount
    await db.update_contract(contract)

    await interaction.followup.send(
        lang_manager.get_text("contract_updated_success", lang).format(name=contract["name"], amount=amount),
        ephemeral=True
    )

@bot.tree.command(name="deletecontract", description="❌ Удалить контракт")
@app_commands.describe(name="Название контракта")
async def delete_contract(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    lang = await db.get_user_language(interaction.user.id)
    contract = await db.get_contract_by_name(name)

    if not contract or contract.get("is_archived", False):
        await interaction.followup.send(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return

    if contract.get("author_id") != interaction.user.id and not is_admin_or_role(interaction.user):
        await interaction.followup.send(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    await db.delete_contract_by_name(name)
    await interaction.followup.send(
        lang_manager.get_text("contract_deleted_success", lang).format(name=name),
        ephemeral=True
    )

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
                default="\n".join(contract.get("participants", []) or [f"<@{contract['author_id']}>"])
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
            lines = "\n".join(f"• {p}" for p in participants)

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
            contract = await db.get_contract_by_name(selected)
            if not contract:
                if not select_interaction.response.is_done():
                    await select_interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
                else:
                    await select_interaction.followup.send(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
                return

            await select_interaction.response.send_modal(ParticipantModal(contract))

    await interaction.followup.send(lang_manager.get_text("select_contract", lang), view=ReportView(), ephemeral=True)

@bot.tree.command(name="reportdays", description="📊 Отчёт за N дней")
@app_commands.describe(days="Сколько дней учитывать (максимум 30)")
async def report_days(interaction: discord.Interaction, days: int):
    await interaction.response.defer(ephemeral=True)
    lang = await db.get_user_language(interaction.user.id)

    if days > Config.MAX_REPORT_DAYS:
        days = Config.MAX_REPORT_DAYS

    now = datetime.now(timezone.utc)
    threshold = now - timedelta(days=days)
    contracts = await db.get_all_contracts()

    recent = []
    for c in contracts:
        if c.get("is_archived", False):
            continue
        try:
            c_time = datetime.fromisoformat(c.get("timestamp", "2000-01-01T00:00:00+00:00"))
            if c_time >= threshold:
                recent.append(c)
        except Exception:
            continue

    if not recent:
        await interaction.followup.send(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    total = sum(c["amount"] for c in recent)
    fund = total * Config.FUND_PERCENTAGE
    payout = total - fund

    earnings = {}
    for contract in recent:
        participants = contract.get("participants", []) or [f"<@{contract['author_id']}>"]
        per_user = round((contract["amount"] - contract["amount"] * Config.FUND_PERCENTAGE) / len(participants), 2)
        for p in participants:
            earnings[p] = earnings.get(p, 0) + per_user

    earnings_lines = "\n".join(f"• {user} — {earned:.2f} USD" for user, earned in sorted(earnings.items(), key=lambda x: -x[1]))

    text = lang_manager.get_text("report_days_summary", lang).format(
        days=days,
        total=f"{total:.2f}",
        fund=f"{fund:.2f}",
        payout=f"{payout:.2f}",
        earnings=earnings_lines
    )

    await interaction.followup.send(text, ephemeral=True)

@bot.tree.command(name="reportlog", description="📜 Просмотр всех сохранённых отчётов")
async def report_log(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    lang = await db.get_user_language(interaction.user.id)
    reports = await db.get_all_reports()
    if not reports:
        await interaction.followup.send(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    lines = []
    for r in reports[-10:]:  # Последние 10 отчётов
        time_str = r.get("timestamp", "")[:19].replace("T", " ")
        lines.append(f"**{r.get('contract_name')}** ({time_str})\nАвтор: <@{r.get('author_id')}>\n{r.get('message')}\n")

    await interaction.followup.send("\n\n".join(lines), ephemeral=True)

@bot.tree.command(name="backup", description="💾 Выгрузка всех данных JSON (только для админов)")
async def backup(interaction: discord.Interaction):
    if not is_admin_or_role(interaction.user):
        lang = await db.get_user_language(interaction.user.id)
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    contracts = await db.get_all_contracts()
    reports = await db.get_all_reports()

    import json
    backup_data = {
        "contracts": contracts,
        "reports": reports
    }
    json_str = json.dumps(backup_data, indent=2, ensure_ascii=False)

    # Отправляем файл через in-memory буфер
    fp = io.StringIO(json_str)
    fp.seek(0)
    await interaction.followup.send("Резервная копия данных:", ephemeral=True)
    await interaction.followup.send(file=discord.File(fp, filename="backup.json"))

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

# Flask для UptimeRobot и Cloudflare
app = Flask('')

@app.route('/')
def home():
    print("✅ Flask получил пинг от Cloudflare")
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
        print("❌ DISCORD_BOT_TOKEN не установлен.")
        exit(1)

    bot.run(token)
