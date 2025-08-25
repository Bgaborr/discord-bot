import discord
from discord.ext import commands
import os
import json
from datetime import datetime
import requests

TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_USER_ID = 442375796804550716  # Cseréld le a megadott felhasználó Discord ID-jére
DATA_FILE = "duty_data.json"
WEBHOOK_URL = "https://discord.com/api/webhooks/1409565434826592306/I9UfoJh-4EEMJJlkb_dNePfTxXIM1tSOd7B4hGow8YbLbVYUtqd_fgc_0h57OnToc_bg"  # Cseréld ki a saját webhook URL-re

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

@bot.event
async def on_ready():
    print(f"Bejelentkezve: {bot.user}")
    save_data() 

@bot.command(name="addido")
async def add_ido(ctx, *, ido: str = None):
    user_id = ctx.author.id
    current_month = get_current_month()
    if not ido:
        await ctx.send("Adj meg egy időt! Példa: `!addido 18:00`")
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
        total_hours = user_data[user_id][current_month]["total_time"] // 60
        total_mins = user_data[user_id][current_month]["total_time"] % 60
        await ctx.send(f"Idő hozzáadva: {ido}. Új összes ({current_month}): {total_hours}:{total_mins:02d}")
        save_data()
    except ValueError:
        await ctx.send("Hibás formátum. Használj HH:MM formátumot.")

@bot.command(name="ido")
async def show_total(ctx):
    user_id = ctx.author.id
    current_month = get_current_month()
    username = ctx.author.name
    if user_id not in user_data or not any(user_data[user_id].values()):
        await ctx.send("Nincs eltárolt idő.")
        return

    # Összes idő kiszámítása az összes hónapból
    total_all_time = sum(data["total_time"] for data in user_data[user_id].values() if "total_time" in data)
    total_all_hours = total_all_time // 60
    total_all_mins = total_all_time % 60

    # Jelenlegi hónap ideje
    current_time = user_data[user_id][current_month]["total_time"] if current_month in user_data[user_id] else 0
    current_hours = current_time // 60
    current_mins = current_time % 60

    # Embed struktúra a Lua kódhoz hasonlóan
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
                "text": f"Bgabor || {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {username} _aduty_ :)"
            }
        }]
    }

    # Webhook küldése hibakereséssel
    try:
        response = requests.post(WEBHOOK_URL, json=embed, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        print("Webhook válasz:", response.text)  # Hibakeresés a konzolban
        await ctx.send("Adatok elküldve a webhookra!")
    except requests.exceptions.RequestException as e:
        print(f"Webhook hiba: {e}")  # Hibakeresés a konzolban
        await ctx.send("Hiba a webhook küldése közben. Ellenőrizd az URL-t vagy a konzolt.")

@bot.command(name="idolog")
async def show_log(ctx, discord_name: str = None, month: str = None):
    if ctx.author.id != ALLOWED_USER_ID:
        await ctx.send("Nincs jogosultságod mások logjának megtekintésére!")
        return
    if not discord_name:
        await ctx.send("Adj meg egy Discord nevet! Példa: `!idolog bgabor_ [YYYY-MM]`")
        return
    user = discord.utils.get(ctx.guild.members, display_name=discord_name)
    if not user:
        await ctx.send(f"Nem található ilyen felhasználó: {discord_name}")
        return
    user_id = user.id
    target_month = month if month else get_current_month()
    if user_id not in user_data or target_month not in user_data[user_id] or not user_data[user_id][target_month]["log"]:
        await ctx.send(f"Nincs log bejegyzés {discord_name} számára {target_month} hónapra.")
    else:
        lista = "\n".join(f"{i+1}. {ts}: +{orig} ({added // 60}:{added % 60:02d})" for i, (ts, added, orig) in enumerate(user_data[user_id][target_month]["log"]))
        await ctx.send(f"{discord_name} idő logja ({target_month}):\n{lista}")

@bot.command(name="torolido")
async def delete_ido(ctx, index: int = None):
    user_id = ctx.author.id
    current_month = get_current_month()
    if user_id not in user_data or current_month not in user_data[user_id]:
        await ctx.send(f"Nincs eltárolt időd {current_month} hónapra.")
        return
    if index is None:
        await ctx.send("Adj meg egy sorszámot a logból! Példa: `!torolido 1`")
        return
    if index < 1 or index > len(user_data[user_id][current_month]["log"]):
        await ctx.send("Érvénytelen sorszám. Használd az `!idolog` parancsot a sorszámok megtekintéséhez.")
        return
    index -= 1  # Átalakítás 0-alapú indexre
    timestamp, minutes, orig = user_data[user_id][current_month]["log"].pop(index)
    user_data[user_id][current_month]["total_time"] -= minutes
    total_hours = user_data[user_id][current_month]["total_time"] // 60
    total_mins = user_data[user_id][current_month]["total_time"] % 60
    await ctx.send(f"Törölve: {timestamp} - {orig}. Új összes ({current_month}): {total_hours}:{total_mins:02d}")
    save_data()

@bot.command(name="lezar")
async def lezar(ctx):
    user_id = ctx.author.id
    current_month = get_current_month()
    if user_id not in user_data or current_month not in user_data[user_id]:
        await ctx.send(f"Nincs eltárolt időd {current_month} hónapra.")
    else:
        user_data[user_id][current_month]["total_time"] = 0
        user_data[user_id][current_month]["log"] = []
        await ctx.send(f"Az idő összesítésed és logod törölve ({current_month}).")
        save_data()

@bot.command(name="hlezar")
async def havi_lezar(ctx):
    if ctx.author.id != ALLOWED_USER_ID:
        await ctx.send("Nincs jogosultságod a havi lezárás végrehajtására!")
        return
    current_month = get_current_month()
    for user_id in user_data:
        if current_month in user_data[user_id]:
            user_data[user_id][current_month]["total_time"] = 0
            user_data[user_id][current_month]["log"] = []
    await ctx.send(f"{current_month} hónap lezárva, új hónap elkezdve.")
    save_data()

bot.run(TOKEN)