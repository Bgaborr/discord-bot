import discord
from discord.ext import commands

import os
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Összes idő percekben
total_time = 0

# Log: lista (időbélyeg, hozzáadott percek, eredeti string)
log = []

@bot.event
async def on_ready():
    print(f"Bejelentkezve: {bot.user}")

@bot.command(name="addido")
async def add_ido(ctx, *, ido: str = None):
    global total_time
    if not ido:
        await ctx.send("Adj meg egy időt! Példa: `!addido 18:00`")
        return
    try:
        hours, minutes = map(int, ido.split(':'))
        added_minutes = hours * 60 + minutes
        total_time += added_minutes
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.append((timestamp, added_minutes, ido))
        total_hours = total_time // 60
        total_mins = total_time % 60
        await ctx.send(f"Idő hozzáadva: {ido}. Új összes: {total_hours}:{total_mins:02d}")
    except ValueError:
        await ctx.send("Hibás formátum. Használj HH:MM formátumot.")

@bot.command(name="ido")
async def show_total(ctx):
    global total_time
    if total_time == 0:
        await ctx.send("Nincs eltárolt idő.")
    else:
        total_hours = total_time // 60
        total_mins = total_time % 60
        await ctx.send(f"Összes idő: {total_hours}:{total_mins:02d}")

@bot.command(name="idolog")
async def show_log(ctx):
    if not log:
        await ctx.send("Nincs log bejegyzés.")
    else:
        lista = "\n".join(f"{ts}: +{orig} ({added // 60}:{added % 60:02d})" for ts, added, orig in log)
        await ctx.send(f"Idő log:\n{lista}")

@bot.command(name="lezar")
async def lezar(ctx):
    global total_time, log
    total_time = 0
    log = []
    await ctx.send("Az idő összesítés és log törölve (lezárva).")

bot.run(TOKEN)