import os
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta, timezone
import io

from core.database_supabase import DatabaseManager
from core.language import LanguageManager
from config import Config

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=Config.COMMAND_PREFIX, intents=intents)

db = DatabaseManager()
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

@bot.tree.command(name="addcontract", description="➕ Добавить контракт")
@app_commands.describe(name="Название контракта", amount="Сумма контракта")
async def add_contract(interaction: discord.Interaction, name: str, amount: float):
    lang = db.get_user_language(interaction.user.id)
    if amount <= 0:
        await interaction.response.send_message(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
        return

    if len(name.strip()) == 0:
        await interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
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

    db.add_contract(contract)
    await interaction.response.send_message(
        lang_manager.get_text("contract_added", lang).format(name=contract["name"], amount=amount)
    )

@bot.tree.command(name="editcontract", description="✏️ Редактировать контракт")
@app_commands.describe(name="Название контракта", amount="Новая сумма")
async def edit_contract(interaction: discord.Interaction, name: str, amount: float):
    lang = db.get_user_language(interaction.user.id)
    contract = db.get_contract_by_name(name)

    if not contract or contract.get("is_archived", False):
        await interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return

    if contract.get("author_id") != interaction.user.id:
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message(lang_manager.get_text("invalid_amount", lang), ephemeral=True)
        return

    contract["amount"] = amount
    db.update_contract(contract)

    await interaction.response.send_message(
        lang_manager.get_text("contract_updated_success", lang).format(name=contract["name"], amount=amount)
    )

@bot.tree.command(name="deletecontract", description="❌ Удалить контракт")
@app_commands.describe(name="Название контракта")
async def delete_contract(interaction: discord.Interaction, name: str):
    lang = db.get_user_language(interaction.user.id)
    contract = db.get_contract_by_name(name)

    if not contract or contract.get("is_archived", False):
        await interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
        return

    if contract.get("author_id") != interaction.user.id and not is_admin_or_role(interaction.user):
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
        for c in contracts if not c.get("is_archived", False)
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
            db.update_contract(self.contract)

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
            contract = db.get_contract_by_name(selected)
            if not contract:
                if not select_interaction.response.is_done():
                    await select_interaction.response.send_message(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
                else:
                    await select_interaction.followup.send(lang_manager.get_text("contract_not_found", lang), ephemeral=True)
                return

            await select_interaction.response.send_modal(ParticipantModal(contract))

    await interaction.response.send_message(lang_manager.get_text("select_contract", lang), view=ReportView(), ephemeral=True)

@bot.tree.command(name="reportlog", description="📜 Просмотр всех сохранённых отчётов")
async def report_log(interaction: discord.Interaction):
    lang = db.get_user_language(interaction.user.id)
    reports = db.get_all_reports()
    if not reports:
        await interaction.response.send_message(lang_manager.get_text("no_contracts_found", lang), ephemeral=True)
        return

    lines = []
    for r in reports[-10:]:  # Последние 10 отчётов
        time_str = r.get("timestamp", "")[:19].replace("T", " ")
        lines.append(f"**{r.get('contract_name')}** ({time_str})\nАвтор: <@{r.get('author_id')}>\n{r.get('report_text')}\n")

    await interaction.response.send_message("\n\n".join(lines), ephemeral=True)

@bot.tree.command(name="backup", description="💾 Выгрузка всех данных JSON (только для админов)")
async def backup(interaction: discord.Interaction):
    if not is_admin_or_role(interaction.user):
        lang = db.get_user_language(interaction.user.id)
        await interaction.response.send_message(lang_manager.get_text("no_permission", lang), ephemeral=True)
        return

    contracts = db.get_all_contracts(include_archived=True)
    reports = db.get_all_reports()

    import json
    backup_data = {
        "contracts": contracts,
        "reports": reports
    }
    json_str = json.dumps(backup_data, indent=2, ensure_ascii=False)

    # Отправляем файл через in-memory буфер
    fp = io.StringIO(json_str)
    fp.seek(0)
    await interaction.response.send_message("Резервная копия данных:", ephemeral=True)
    await interaction.followup.send(file=discord.File(fp, filename="backup.json"))

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
    await interaction.response.send_message(embed=embed, ephemeral=True)

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
