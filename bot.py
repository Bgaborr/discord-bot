import discord
from discord.ext import commands
import requests
import os
from datetime import datetime
import threading
from flask import Flask
from pymongo import MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError, PyMongoError
import time

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
ALLOWED_USER_IDS = [442375796804550716] 
WEBHOOK_URL = "https://discord.com/api/webhooks/1409565434826592306/I9UfoJh-4EEMJJlkb_dNePfTxXIM1tSOd7B4hGow8YbLbVYUtqd_fgc_0h57OnToc_bg"

# MongoDB kapcsolat
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://gabe:Almafa1234@bot.ngypdsp.mongodb.net/?retryWrites=true&w=majority&appName=Bot")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30000)
    client.admin.command('ping')  # Ping a szerverhez
    print("Sikeres MongoDB kapcsolat és hitelesítés!")
except ServerSelectionTimeoutError as sse:
    print(f"MongoDB kapcsolat időtúllépés hiba: {sse}")
    raise
except OperationFailure as oe:
    print(f"Hitelesítési hiba: {oe}")
    raise
except PyMongoError as pe:
    print(f"Általános MongoDB hiba: {pe}")
    raise
db = client["duty_data"]
collection = db["user_data"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bejelentkezve: {bot.user}")

def load_user_data():
    user_data = {}
    try:
        for doc in collection.find():
            user_id = doc["user_id"]
            if user_id not in user_data:
                user_data[user_id] = {}
            user_data[user_id][doc["month"]] = {"total_time": doc["total_time"], "log": doc.get("log", [])}
    except PyMongoError as e:
        print(f"Hiba az adatok betöltésekor: {e}")
    return user_data

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
    except PyMongoError as e:
        print(f"Hiba az adatok mentésekor: {e}")

def get_current_month():
    return datetime.now().strftime("%Y-%m")

def create_embed(username, title, description, color=16711680, fields=None):
    return {
        "embeds": [{
            "color": color,
            "title": f"**{title}**",
            "description": f"{description}\n\n**Felhasználó:** {username}",
            "fields": fields or [],
            "footer": {"text": f"Bgabor || {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "}
        }]
    }

def send_webhook(embed):
    try:
        response = requests.post(WEBHOOK_URL, json=embed, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Webhook hiba: {e}")

@bot.command(name="idoadd")
async def add_ido(ctx, *, ido: str = None):
    user_id = ctx.author.id
    username = ctx.author.name
    current_month = get_current_month()

    if not ido:
        embed = create_embed(username, "Hiba", "Adj meg egy időt! Példa: `!idoadd 18:00`", color=16711680)
        send_webhook(embed)
        return

    try:
        if ':' in ido:
            hours, minutes = map(int, ido.split(':'))
        elif ' ' in ido:
            hours, minutes = map(int, ido.split(' '))
        else:
            embed = create_embed(username, "Hiba", "Hibás formátum. Használj HH:MM vagy HH MM formátumot.", color=16711680)
            send_webhook(embed)
            return

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

        fields = [
            {"name": "Idő hozzáadva", "value": ido, "inline": True},
            {"name": "Új összes", "value": f"{total_hours}:{total_mins:02d} ({current_month})", "inline": True}
        ]
        embed = create_embed(username, "Idő hozzáadva", "Sikeres mentés!", color=3066993, fields=fields)  # zöld
        send_webhook(embed)
        save_data(user_data)

    except ValueError:
        embed = create_embed(username, "Hiba", "Hibás formátum. Használj HH:MM vagy HH MM formátumot.", color=16711680)
        send_webhook(embed)

@bot.command(name="ido")
async def show_total(ctx):
    user_id = ctx.author.id
    username = ctx.author.name
    current_month = get_current_month()

    if user_id not in user_data:
        return

    total_all_time = sum(data["total_time"] for data in user_data[user_id].values())
    total_all_hours = total_all_time // 60
    total_all_mins = total_all_time % 60

    current_time = user_data[user_id].get(current_month, {}).get("total_time", 0)
    current_hours = current_time // 60
    current_mins = current_time % 60

    fields = [
        {"name": "Összes Duty Idő", "value": f"{total_all_hours}h {total_all_mins}m", "inline": True},
        {"name": "Jelenlegi Duty Idő", "value": f"{current_hours}h {current_mins}m", "inline": True}
    ]
    embed = create_embed(username, "Duty idő", "Duty lekérdezés", color=3447003, fields=fields)  # kék
    send_webhook(embed)

@bot.command(name="idolog")
async def show_log(ctx, discord_name: str = None, month: str = None):
    if ctx.author.id not in ALLOWED_USER_IDS:
        embed = create_embed(ctx.author.name, "Hiba", "Nincs jogosultságod más logját megnézni!", color=16711680)
        send_webhook(embed)
        return

    if not discord_name:
        embed = create_embed(ctx.author.name, "Hiba", "Adj meg egy nevet! Példa: `!idolog felhasználónév [YYYY-MM]`", color=16711680)
        send_webhook(embed)
        return

    user = discord.utils.get(ctx.guild.members, name=discord_name)
    if not user:
        embed = create_embed(ctx.author.name, "Hiba", "Nem található ilyen felhasználó.", color=16711680)
        send_webhook(embed)
        return

    user_id = user.id
    target_month = month if month else get_current_month()

    if user_id not in user_data or target_month not in user_data[user_id] or not user_data[user_id][target_month]["log"]:
        embed = create_embed(discord_name, "Idő log", f"Nincs log bejegyzés {target_month} hónapra.", color=15158332)  # narancs
        send_webhook(embed)
    else:
        lista = "\n".join(
            f"{i+1}. {ts}: {'+' if added > 0 else '-'}{abs(orig)} ({'-' if added < 0 else ''}{abs(added)//60}:{abs(added)%60:02d})"
            for i, (ts, added, orig) in enumerate(user_data[user_id][target_month]["log"])
        )
        embed = create_embed(discord_name, "Idő log", f"{discord_name} idő logja ({target_month}):\n{lista}", color=15158332)  # narancs
        send_webhook(embed)

@bot.command(name="torolido")
async def delete_ido(ctx, *, ido: str = None):
    user_id = ctx.author.id
    username = ctx.author.name
    current_month = get_current_month()

    if user_id not in user_data or current_month not in user_data[user_id]:
        embed = create_embed(username, "Hiba", f"Nincs eltárolt időd {current_month} hónapra.", color=16711680)
        send_webhook(embed)
        return

    if not ido:
        embed = create_embed(username, "Hiba", "Adj meg egy időt! Példa: `!torolido 1:30` vagy `!torolido 90`", color=16711680)
        send_webhook(embed)
        return

    try:
        # Idő feldolgozása (HH:MM vagy perc)
        if ':' in ido:
            hours, minutes = map(int, ido.split(':'))
            remove_minutes = hours * 60 + minutes
        elif ido.isdigit():
            remove_minutes = int(ido)
        else:
            embed = create_embed(username, "Hiba", "Hibás formátum. Használj HH:MM vagy csak perceket!", color=16711680)
            send_webhook(embed)
            return

        # Ha nincs elég idő levonni
        if user_data[user_id][current_month]["total_time"] < remove_minutes:
            embed = create_embed(username, "Hiba", f"Nincs ennyi időd, csak {user_data[user_id][current_month]['total_time']//60}h {user_data[user_id][current_month]['total_time']%60}m van rögzítve.", color=16711680)
            send_webhook(embed)
            return

        # Idő levonása és logolása
        user_data[user_id][current_month]["total_time"] -= remove_minutes
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_data[user_id][current_month]["log"].append((timestamp, -remove_minutes, ido))

        total_hours = user_data[user_id][current_month]["total_time"] // 60
        total_mins = user_data[user_id][current_month]["total_time"] % 60

        fields = [
            {"name": "Idő törölve", "value": f"-{ido}", "inline": True},
            {"name": "Új összes", "value": f"{total_hours}:{total_mins:02d} ({current_month})", "inline": True}
        ]
        embed = create_embed(username, "Idő törölve", "Sikeresen levonva az időből!", color=15105570, fields=fields)  # narancs/pirosas
        send_webhook(embed)
        save_data(user_data)

    except ValueError:
        embed = create_embed(username, "Hiba", "Hibás formátum. Használj HH:MM vagy csak perceket!", color=16711680)
        send_webhook(embed)
@bot.command(name="help")
async def show_help(ctx):
    username = ctx.author.name

    fields = [
        {"name": "!idoadd <HH:MM / HH MM>", 
         "value": "Idő hozzáadása a saját duty idődhöz.\nPélda: `!idoadd 1:30` vagy `!idoadd 90`", "inline": False},
        {"name": "!torolido <HH:MM / percek>", 
         "value": "Idő levonása a saját duty idődből.\nPélda: `!torolido 0:45` vagy `!torolido 45`", "inline": False},
        {"name": "!ido", 
         "value": "Megmutatja az összes eddigi és a hónapban gyűjtött duty időt.", "inline": False},
        {"name": "!idolog <felhasználónév> [YYYY-MM]", 
         "value": "Megmutatja egy felhasználó idő logját. Csak engedélyezett felhasználóknak.", "inline": False},
        {"name": "!help", 
         "value": "Ez a súgó, ami felsorolja az összes parancsot és használatukat.", "inline": False}
    ]

    embed = create_embed(
        username,
        "Duty Bot Súgó",
        "Itt találod az összes elérhető parancs magyarázatát:",
        color=16975,  
        fields=fields
    )

    send_webhook(embed)
bot.run(TOKEN)
