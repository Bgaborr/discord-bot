import discord
from discord.ext import commands

import os

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# időpontok tárolása
idopontok = []

@bot.event
async def on_ready():
    print(f"Bejelentkezve: {bot.user}")

@bot.command(name="addido")
async def add_ido(ctx, *, ido: str = None):
    if not ido:
        await ctx.send("Adj meg egy időpontot! Példa: `!addido 18:00`")
        return
    idopontok.append(ido)
    await ctx.send(f"Időpont hozzáadva: {ido}")

@bot.command(name="ido")
async def list_ido(ctx):
    if not idopontok:
        await ctx.send("Nincs eltárolt időpont.")
    else:
        lista = "\n".join(f"{i+1}. {idop}" for i, idop in enumerate(idopontok))
        await ctx.send(f"Eddigi időpontok:\n{lista}")

@bot.command(name="lezar")
async def lezar(ctx):
    global idopontok
    idopontok = []
    await ctx.send("Az időpontok listája törölve (lezárva).")

bot.run(TOKEN)
