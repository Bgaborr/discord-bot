import discord
from discord.ext import commands
import os
import json
from datetime import datetime
import requests

TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_USER_ID = 442375796804550716  # A te megadott ID-d
DATA_FILE = "duty_data.json"
WEBHOOK_URL = "https://discord.com/api/webhooks/1409565434826592306/I9UfoJh-4EEMJJlkb_dNePfTxXIM1tSOd7B4hGow8YbLbVYUtqd_fgc_0h57OnToc_bg"  # A te webhook URL-d

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  
bot = commands.Bot(command_prefix="!", intents=intents)

# Adatok betöltése JSON-ból induláskor
try:
    with open(DATA_FILE, 'r') as f:
        user_data = json.load(f)
except FileNotFoundError:
    user_data = {}

def get_current_month():
    return datetime.now().strftime("%Y-%m")

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(user_data, f, indent=4)

def send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins):
    embed = {
        "embeds": [{
            "color": 27946,  # Zöld szín a képen látható stílushoz
            "title": f"**{username}**",
            "description": "Duty lekérdezés",
            "fields": [
                {
                    "name": "Összes Duty Idő",
                    "value": f"{total_all_hours}h {total_all_mins}m",
                    "inline": True
                },
                {
                    "name": "Jelenlegi Duty Idő",
                    "value": f"{current_hours}h {current_mins}m",
                    "inline": True
                }
            ],
            "footer": {
                "text": f"Bgabor || {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }]
    }
    try:
        response = requests.post(WEBHOOK_URL, json=embed, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        print("Webhook válasz:", response.text)  # Hibakeresés a konzolban
    except requests.exceptions.RequestException as e:
        print(f"Webhook hiba: {e}")  # Hibakeresés a konzolban

@bot.event
async def on_ready():
    print(f"Bejelentkezve: {bot.user}")
    save_data()  # Mentés induláskor, ha új fájl

@bot.command(name="addido")
async def add_ido(ctx, *, ido: str = None):
    user_id = ctx.author.id
    current_month = get_current_month()
    username = ctx.author.name
    if not ido:
        total_all_time = sum(data["total_time"] for data in user_data.get(user_id, {}).values() if "total_time" in data)
        total_all_hours = total_all_time // 60
        total_all_mins = total_all_time % 60
        current_time = user_data.get(user_id, {}).get(current_month, {"total_time": 0})["total_time"]
        current_hours = current_time // 60
        current_mins = current_time % 60
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
        return
    try:
        hours, minutes = map(int, ido.split(':'))
        added_minutes = hours * 60 + minutes
        if user_id not in user_data:
            user_data[user_id] = {}
        if current_month not in user_data[user_id]:
            user_data[user_id][current_month] = {"total_time": 0, "log": []}
        user_data[user_id][current_month]["total_time"] += added_minutes
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_data[user_id][current_month]["log"].append((timestamp, added_minutes, ido))
        total_all_time = sum(data["total_time"] for data in user_data[user_id].values() if "total_time" in data)
        total_all_hours = total_all_time // 60
        total_all_mins = total_all_time % 60
        current_time = user_data[user_id][current_month]["total_time"]
        current_hours = current_time // 60
        current_mins = current_time % 60
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
        save_data()
    except ValueError:
        total_all_time = sum(data["total_time"] for data in user_data.get(user_id, {}).values() if "total_time" in data)
        total_all_hours = total_all_time // 60
        total_all_mins = total_all_time % 60
        current_time = user_data.get(user_id, {}).get(current_month, {"total_time": 0})["total_time"]
        current_hours = current_time // 60
        current_mins = current_time % 60
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)

@bot.command(name="ido")
async def show_total(ctx):
    user_id = ctx.author.id
    current_month = get_current_month()
    username = ctx.author.name
    if user_id not in user_data or not any(user_data[user_id].values()):
        total_all_hours = 0
        total_all_mins = 0
        current_hours = 0
        current_mins = 0
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
        return
    total_all_time = sum(data["total_time"] for data in user_data[user_id].values() if "total_time" in data)
    total_all_hours = total_all_time // 60
    total_all_mins = total_all_time % 60
    current_time = user_data[user_id][current_month]["total_time"] if current_month in user_data[user_id] else 0
    current_hours = current_time // 60
    current_mins = current_time % 60
    await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)

@bot.command(name="idolog")
async def show_log(ctx, discord_name: str = None, month: str = None):
    if ctx.author.id != ALLOWED_USER_ID:
        username = ctx.author.name
        total_all_time = sum(data["total_time"] for data in user_data.get(ctx.author.id, {}).values() if "total_time" in data)
        total_all_hours = total_all_time // 60
        total_all_mins = total_all_time % 60
        current_time = user_data.get(ctx.author.id, {}).get(get_current_month(), {"total_time": 0})["total_time"]
        current_hours = current_time // 60
        current_mins = current_time % 60
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
        return
    if not discord_name:
        username = ctx.author.name
        total_all_time = sum(data["total_time"] for data in user_data.get(ctx.author.id, {}).values() if "total_time" in data)
        total_all_hours = total_all_time // 60
        total_all_mins = total_all_time % 60
        current_time = user_data.get(ctx.author.id, {}).get(get_current_month(), {"total_time": 0})["total_time"]
        current_hours = current_time // 60
        current_mins = current_time % 60
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
        return
    user = discord.utils.get(ctx.guild.members, display_name=discord_name)
    if not user:
        username = ctx.author.name
        total_all_time = sum(data["total_time"] for data in user_data.get(ctx.author.id, {}).values() if "total_time" in data)
        total_all_hours = total_all_time // 60
        total_all_mins = total_all_time % 60
        current_time = user_data.get(ctx.author.id, {}).get(get_current_month(), {"total_time": 0})["total_time"]
        current_hours = current_time // 60
        current_mins = current_time % 60
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
        return
    user_id = user.id
    target_month = month if month else get_current_month()
    if user_id not in user_data or target_month not in user_data[user_id] or not user_data[user_id][target_month]["log"]:
        username = discord_name
        total_all_time = sum(data["total_time"] for data in user_data.get(user_id, {}).values() if "total_time" in data)
        total_all_hours = total_all_time // 60
        total_all_mins = total_all_time % 60
        current_time = user_data.get(user_id, {}).get(target_month, {"total_time": 0})["total_time"]
        current_hours = current_time // 60
        current_mins = current_time % 60
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
        return
    lista = "\n".join(f"{i+1}. {ts}: +{orig} ({added // 60}:{added % 60:02d})" for i, (ts, added, orig) in enumerate(user_data[user_id][target_month]["log"]))
    username = discord_name
    total_all_time = sum(data["total_time"] for data in user_data.get(user_id, {}).values() if "total_time" in data)
    total_all_hours = total_all_time // 60
    total_all_mins = total_all_time % 60
    current_time = user_data.get(user_id, {}).get(target_month, {"total_time": 0})["total_time"]
    current_hours = current_time // 60
    current_mins = current_time % 60
    await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)

@bot.command(name="torolido")
async def delete_ido(ctx, index: int = None):
    user_id = ctx.author.id
    current_month = get_current_month()
    username = ctx.author.name
    if user_id not in user_data or current_month not in user_data[user_id]:
        total_all_time = sum(data["total_time"] for data in user_data.get(user_id, {}).values() if "total_time" in data)
        total_all_hours = total_all_time // 60
        total_all_mins = total_all_time % 60
        current_time = user_data.get(user_id, {}).get(current_month, {"total_time": 0})["total_time"]
        current_hours = current_time // 60
        current_mins = current_time % 60
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
        return
    if index is None:
        total_all_time = sum(data["total_time"] for data in user_data.get(user_id, {}).values() if "total_time" in data)
        total_all_hours = total_all_time // 60
        total_all_mins = total_all_time % 60
        current_time = user_data.get(user_id, {}).get(current_month, {"total_time": 0})["total_time"]
        current_hours = current_time // 60
        current_mins = current_time % 60
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
        return
    if index < 1 or index > len(user_data[user_id][current_month]["log"]):
        total_all_time = sum(data["total_time"] for data in user_data.get(user_id, {}).values() if "total_time" in data)
        total_all_hours = total_all_time // 60
        total_all_mins = total_all_time % 60
        current_time = user_data.get(user_id, {}).get(current_month, {"total_time": 0})["total_time"]
        current_hours = current_time // 60
        current_mins = current_time % 60
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
        return
    index -= 1  # Átalakítás 0-alapú indexre
    timestamp, minutes, orig = user_data[user_id][current_month]["log"].pop(index)
    user_data[user_id][current_month]["total_time"] -= minutes
    total_all_time = sum(data["total_time"] for data in user_data[user_id].values() if "total_time" in data)
    total_all_hours = total_all_time // 60
    total_all_mins = total_all_time % 60
    current_time = user_data[user_id][current_month]["total_time"]
    current_hours = current_time // 60
    current_mins = current_time % 60
    await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
    save_data()

@bot.command(name="lezar")
async def lezar(ctx):
    user_id = ctx.author.id
    current_month = get_current_month()
    username = ctx.author.name
    if user_id not in user_data or current_month not in user_data[user_id]:
        total_all_time = sum(data["total_time"] for data in user_data.get(user_id, {}).values() if "total_time" in data)
        total_all_hours = total_all_time // 60
        total_all_mins = total_all_time % 60
        current_time = user_data.get(user_id, {}).get(current_month, {"total_time": 0})["total_time"]
        current_hours = current_time // 60
        current_mins = current_time % 60
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
        return
    user_data[user_id][current_month]["total_time"] = 0
    user_data[user_id][current_month]["log"] = []
    total_all_time = sum(data["total_time"] for data in user_data.get(user_id, {}).values() if "total_time" in data)
    total_all_hours = total_all_time // 60
    total_all_mins = total_all_time % 60
    current_time = user_data[user_id][current_month]["total_time"]
    current_hours = current_time // 60
    current_mins = current_time % 60
    await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
    save_data()

@bot.command(name="hlezar")
async def havi_lezar(ctx):
    if ctx.author.id != ALLOWED_USER_ID:
        username = ctx.author.name
        total_all_time = sum(data["total_time"] for data in user_data.get(ctx.author.id, {}).values() if "total_time" in data)
        total_all_hours = total_all_time // 60
        total_all_mins = total_all_time % 60
        current_time = user_data.get(ctx.author.id, {}).get(get_current_month(), {"total_time": 0})["total_time"]
        current_hours = current_time // 60
        current_mins = current_time % 60
        await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
        return
    current_month = get_current_month()
    for user_id in user_data:
        if current_month in user_data[user_id]:
            user_data[user_id][current_month]["total_time"] = 0
            user_data[user_id][current_month]["log"] = []
    username = ctx.author.name
    total_all_time = sum(data["total_time"] for data in user_data.get(ctx.author.id, {}).values() if "total_time" in data)
    total_all_hours = total_all_time // 60
    total_all_mins = total_all_time % 60
    current_time = user_data.get(ctx.author.id, {}).get(current_month, {"total_time": 0})["total_time"]
    current_hours = current_time // 60
    current_mins = current_time % 60
    await send_embed(ctx, username, total_all_hours, total_all_mins, current_hours, current_mins)
    save_data()

bot.run(TOKEN)