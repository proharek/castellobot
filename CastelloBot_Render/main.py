import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("❌ DISCORD_BOT_TOKEN не установлен в переменных окружения!")

# ----------- Flask веб-сервер для health check -----------

app = Flask(__name__)

@app.route("/healthz")
def healthz():
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ----------- Discord бот -----------

intents = discord.Intents.default()
intents.message_content = True  # если нужно читать содержимое сообщений

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 Бот запущен как {bot.user}!")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# Запускаем Flask в отдельном потоке
flask_thread = Thread(target=run_flask)
flask_thread.start()

# Запускаем Discord бота
bot.run(DISCORD_TOKEN)

