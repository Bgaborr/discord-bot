import discord
from discord.ext import commands
import requests
import os
from datetime import datetime
import threading
from flask import Flask
from pymongo import MongoClient
from pymongo.errors import ConnectionError

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot fut Renderen!"

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Indítsd külön szálon a webservert
threading.Thread(target=run_web).start()

TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_USER_ID = 442375796804550716 
WEBHOOK_URL = "https://discord.com/api/webhooks/1409565434826592306/I9UfoJh-4EEMJJlkb_dNePfTxXIM1tSOd7B4hGow8YbLbVYUtqd_fgc_0h57OnToc_bg"  # A te webhook URL-d

# MongoDB kapcsolat
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://gabe:Almafa1234@bot.ngypdsp.mongodb.net/?retryWrites=true&w=majority&appName=Bot")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30000)  # Növelt időtúllépés
    client.server_info()  # Teszteli a kapcsolatot
    print("Sikeres MongoDB kapcsolat!")
except ConnectionError as e:
    print(f"MongoDB kapcsolat hiba: {e}")
    raise
db = client["duty_data"]
collection = db["user_data"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  
bot = commands.Bot(command_prefix="!", intents=intents)

def load_user_data():
    user_data = {}
    try:
        for doc in collection.find():
            user_id = doc["user_id"]
            if user_id not in user_data:
                user_data[user_id] = {}
            user_data[user_id][doc["month"]] = {"total_time": doc["total_time"], "log": doc.get("log", [])}
    except Exception as e:
        print(f"Hiba az adatok betöltésekor: {e}")
    return user_data

# Globális user_data inicializálása
user_data = load_user_data()

def save_data(user_data):
    try:
        collection.delete_many({})
        for user_id, months in user_data.items():
            for month, data in months.items():
                collection.insert_one({
                    "user_id": user_id,
                    "month": month,
                    "total_time": data["total_time"],
                    "log": data["log"]
                })
    except Exception as e:
        print(f"Hiba az adatok mentésekor: {e}")

def get_current_month():
    return datetime.now().strftime("%Y-%m")

@bot.event
async def on_ready():
    print(f"Bejelentkezve: {bot.user}")

@bot.command(name="idoadd")
async def add_ido(ctx, *, ido: str = None):
    user_id = ctx.author.id
    current_month = get_current_month()
    if not ido:
        await ctx.send("Adj meg egy időt! Példa: `!addido 18:00 (HH MM)` vagy `!addido 18 00(HH MM)`")
        return
    try:
        if ':' in ido:
            hours, minutes = map(int, ido.split(':'))
        elif ' ' in ido:
            hours, minutes = map(int, ido.split(' '))
        else:
            raise ValueError("Hibás formátum. Használj HH:MM vagy HH MM formátumot.")
        
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
        save_data(user_data)
    except ValueError:
        await ctx.send("Hibás formátum. Használj HH:MM vagy HH MM formátumot.")

@bot.command(name="ido")
async def show_total(ctx):
    user_id = ctx.author.id
    current_month = get_current_month()
    username = ctx.author.name
    if user_id not in user_data or not any(user_data[user_id].values()):
        await ctx.send(f"{username}\nNincs eltárolt idő.")
        await ctx.send("Nincs eltárolt idő.")
        return

    total_all_time = sum(data["total_time"] for data in user_data[user_id].values() if "total_time" in data)
    total_all_hours = total_all_time // 60
    total_all_mins = total_all_time % 60

    current_time = user_data[user_id][current_month]["total_time"] if current_month in user_data[user_id] else 0
    current_hours = current_time // 60
    current_mins = current_time % 60

    message = f"{username}\n" \
              f"Összes Duty Idő    {total_all_hours}h {total_all_mins}m\n" \
              f"Jelenlegi Duty Idő {current_hours}h {current_mins}m\n" \
              f"({datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {username} _aduty_)"
    embed = {
        "embeds": [{
            "color": 27946,
            "title": f"**{username}**",
            "description": "Duty lekérdezés",
            "fields": [
                {"name": "Összes Duty Idő", "value": f"{total_all_hours}h {total_all_mins}m", "inline": True},
                {"name": "Jelenlegi Duty Idő", "value": f"{current_hours}h {current_mins}m", "inline": True}
            ],
            "footer": {"text": f"Bgabor || {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {username}"}
        }]
    }

    payload = {"content": message, "username": "Duty Bot"}
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        response = requests.post(WEBHOOK_URL, json=embed, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        await ctx.send("Adatok elküldve a webhookra!")
    except requests.exceptions.RequestException as e:
        await ctx.send("Hiba a webhook küldése közben. Ellenőrizd az URL-t.")
        return

    await ctx.send("Adatok elküldve a webhookra!")

@bot.command(name="idolog")
async def show_log(ctx, discord_name: str = None, month: str = None):
    if ctx.author.id != ALLOWED_USER_ID:
        await ctx.send("Nincs jogosultságod mások logjának megtekintésére!")
        return
    if not discord_name:
        await ctx.send("Adj meg egy Discord nevet! Példa: `!idolog felhasználónév [YYYY-MM]`")
        return
    user = discord.utils.get(ctx.guild.members, name=discord_name)
    if not user:
        await ctx.send("Nem található ilyen felhasználó.")
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
    index -= 1
    timestamp, minutes, orig = user_data[user_id][current_month]["log"].pop(index)
    user_data[user_id][current_month]["total_time"] -= minutes
    total_hours = user_data[user_id][current_month]["total_time"] // 60
    total_mins = user_data[user_id][current_month]["total_time"] % 60
    await ctx.send(f"Törölve: {timestamp} - {orig}. Új összes ({current_month}): {total_hours}:{total_mins:02d}")
    save_data(user_data)

bot.run(TOKEN)