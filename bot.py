import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import aiohttp
import asyncio
import os
import random
import string
import json

from config import (
    BOT_TOKEN, GUILD_ID,
    KANAL_WERYFIKACJI, KANAL_DOWODY, KANAL_WYROKI,
    KANAL_MANDATY, KANAL_FAKTURY, KANAL_LISTY_GONCZE, KANAL_REJESTRACJA,
    KANAL_OGLOSZENIA_RP,
    ROLA_WERYFIKOWANY, ROLA_POLICJA, ROLA_FAKTURY,
    ROLA_LISTY_GONCZE, ROLA_REJESTRACJA, ROLA_DOWOD, ROLA_OGLOSZENIA_RP,
    KANAL_PODANIA_KMP, KANAL_PODANIA_SPD, KANAL_PODANIA_JRG, KANAL_PODANIA_RSPR
)
from database import init_db, get_db

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

def ma_role(member: discord.Member, rola_id: int) -> bool:
    rola = member.guild.get_role(rola_id)
    if not rola: return False
    return rola in member.roles

async def pobierz_dane_roblox(discord_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT roblox_id, roblox_username FROM weryfikacje WHERE discord_id = ?", (discord_id,))
    wynik = cursor.fetchone()
    conn.close()
    return wynik

def generuj_kod():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ═══════════════════════════════════════════════════════
# WEBHOOK - odbieranie podań ze strony
# ═══════════════════════════════════════════════════════
from aiohttp import web

async def webhook_handler(request):
    try:
        data = await request.json()
        frakcja = data.get("frakcja")
        frakcja_nazwa = data.get("frakcjaNazwa")
        discord_id = data.get("discordId")
        discord_username = data.get("discordUsername")
        discord_global = data.get("discordGlobalName", discord_username)
        odpowiedzi = data.get("odpowiedzi", {})
        timestamp = data.get("timestamp", datetime.now().isoformat())

        # Wybierz kanał
        kanaly = {
            "kmp": KANAL_PODANIA_KMP,
            "spd": KANAL_PODANIA_SPD,
            "jrg": KANAL_PODANIA_JRG,
            "rspr": KANAL_PODANIA_RSPR
        }
        kanal_id = kanaly.get(frakcja)
        if not kanal_id:
            return web.Response(status=400, text="Nieznana frakcja")

        guild = bot.get_guild(GUILD_ID)
        if not guild:
            return web.Response(status=500, text="Brak serwera")

        channel = guild.get_channel(kanal_id)
        if not channel:
            return web.Response(status=500, text="Brak kanału")

        # Zbuduj embed
        embed = discord.Embed(
            title=f"📋 Nowe podanie - {frakcja_nazwa}",
            description=f"**Od:** {discord_global} (`{discord_username}`)\n**ID Discord:** `{discord_id}`\n**Data:** {timestamp[:19].replace('T', ' ')}",
            color=0x00D4AA,
            timestamp=datetime.now()
        )

        # Dodaj odpowiedzi
        for key, value in odpowiedzi.items():
            nr = key.replace("p", "")
            # Skróć długie odpowiedzi
            val = value[:1000] + "..." if len(value) > 1000 else value
            embed.add_field(name=f"Pytanie {nr}", value=val or "Brak", inline=False)

        # Sprawdź czy użytkownik jest na serwerze
        member = guild.get_member(int(discord_id))
        if member:
            embed.set_thumbnail(url=member.display_avatar.url)

        await channel.send(embed=embed)

        # Zapisz w bazie
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS podania (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id INTEGER,
                discord_username TEXT,
                frakcja TEXT,
                frakcja_nazwa TEXT,
                odpowiedzi TEXT,
                status TEXT DEFAULT 'oczekujace',
                timestamp TEXT
            )
        ''')
        cursor.execute(
            "INSERT INTO podania (discord_id, discord_username, frakcja, frakcja_nazwa, odpowiedzi, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (discord_id, discord_username, frakcja, frakcja_nazwa, json.dumps(odpowiedzi), timestamp)
        )
        conn.commit()
        conn.close()

        return web.Response(status=200, text="OK")
    except Exception as e:
        print(f"Webhook error: {e}")
        return web.Response(status=500, text=str(e))

async def start_webhook():
    app = web.Application()
    app.router.add_post("/api/podanie", webhook_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    await site.start()
    print(f"✅ Webhook nasłuchuje na porcie {os.getenv('PORT', 8080)}")

# ═══════════════════════════════════════════════════════
# START BOTA
# ═══════════════════════════════════════════════════════
@bot.event
async def on_ready():
    print(f"✅ Bot zalogowany jako: {bot.user}")
    print(f"🌐 Serwerów: {len(bot.guilds)}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synchronizowano {len(synced)} komend")
    except Exception as e:
        print(f"❌ Błąd sync: {e}")
    await odtworz_panel_weryfikacji()
    await start_webhook()

# ═══════════════════════════════════════════════════════
# PANEL WERYFIKACJI
# ═══════════════════════════════════════════════════════
async def odtworz_panel_weryfikacji():
    guild = bot.get_guild(GUILD_ID)
    if not guild: return
    channel = guild.get_channel(KANAL_WERYFIKACJI)
    if not channel: return

    usuniete = 0
    async for msg in channel.history(limit=100):
        if msg.author.id == bot.user.id:
            try:
                await msg.delete()
                usuniete += 1
            except: pass

    if usuniete > 0: print(f"🗑️ Usunięto {usuniete} starych paneli")
    await wyslij_panel_weryfikacji(channel)
    print("✅ Nowy panel weryfikacji wysłany!")

async def wyslij_panel_weryfikacji(channel):
    embed = discord.Embed(
        title="🔐 Weryfikacja Roblox",
        description="Kliknij przycisk, aby zweryfikować konto Roblox.\nPo weryfikacji otrzymasz zmianę nicku i rolę.",
        color=0x00D4AA
    )
    await channel.send(embed=embed, view=WeryfikacjaView())

class WeryfikacjaView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Zweryfikuj się", style=discord.ButtonStyle.green, emoji="✅")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM weryfikacje WHERE discord_id = ?", (interaction.user.id,))
        if cursor.fetchone():
            conn.close()
            await interaction.response.send_message("✅ Już zweryfikowany!", ephemeral=True)
            return
        conn.close()
        await interaction.response.send_modal(WeryfikacjaModal())

class WeryfikacjaModal(discord.ui.Modal, title="Weryfikacja - Krok 1"):
    roblox_nick = discord.ui.TextInput(label="Nick Roblox", placeholder="Dokładny nick", required=True, max_length=50)

    async def on_submit(self, interaction: discord.Interaction):
        nick = self.roblox_nick.value
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://users.roblox.com/v1/users/search?keyword={nick}&limit=10") as resp:
                if resp.status != 200:
                    await interaction.response.send_message("❌ Błąd Roblox API", ephemeral=True)
                    return
                data = await resp.json()
                users = data.get("data", [])
                user = None
                for u in users:
                    if u["name"].lower() == nick.lower():
                        user = u
                        break
                if not user:
                    await interaction.response.send_message(f"❌ Nie znaleziono `{nick}`", ephemeral=True)
                    return
                roblox_id = user["id"]
                roblox_username = user["name"]

        kod = generuj_kod()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO kody_weryfikacyjne (discord_id, kod, roblox_id, roblox_username) VALUES (?, ?, ?, ?)",
                       (interaction.user.id, kod, roblox_id, roblox_username))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="🔐 Krok 1",
            description=f"Konto: `{roblox_username}`\n\n1. Wejdź w About na Roblox\n2. Wpisz kod w Description:\n```\n{kod}\n```\n3. Kliknij Save\n\nMasz 10 minut.",
            color=0xFFA500
        )
        await interaction.response.send_message(embed=embed, view=SprawdzKodView(kod, roblox_id, roblox_username), ephemeral=True)

class SprawdzKodView(discord.ui.View):
    def __init__(self, kod, roblox_id, roblox_username):
        super().__init__(timeout=600)
        self.kod = kod; self.roblox_id = roblox_id; self.roblox_username = roblox_username

    @discord.ui.button(label="Sprawdź kod", style=discord.ButtonStyle.blurple)
    async def sprawdz(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT kod FROM kody_weryfikacyjne WHERE discord_id = ?", (interaction.user.id,))
        wynik = cursor.fetchone()
        if not wynik:
            await interaction.response.send_message("❌ Kod wygasł", ephemeral=True)
            conn.close(); return

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://users.roblox.com/v1/users/{self.roblox_id}") as resp:
                user_data = await resp.json()
                opis = user_data.get("description", "") or ""

        if self.kod not in opis:
            await interaction.response.send_message(f"❌ Kod nie znaleziony w opisie\n```{self.kod}```", ephemeral=True)
            conn.close(); return

        cursor.execute("DELETE FROM kody_weryfikacyjne WHERE discord_id = ?", (interaction.user.id,))
        cursor.execute("INSERT INTO weryfikacje (discord_id, roblox_id, roblox_username) VALUES (?, ?, ?)",
                       (interaction.user.id, self.roblox_id, self.roblox_username))
        conn.commit()
        conn.close()

        try: await interaction.user.edit(nick=self.roblox_username)
        except: pass
        rola = interaction.guild.get_role(ROLA_WERYFIKOWANY)
        if rola: await interaction.user.add_roles(rola)

        embed = discord.Embed(title="✅ Zweryfikowano", description=f"Nick: {self.roblox_username}", color=0x00FF00)
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

# ═══════════════════════════════════════════════════════
# KOMENDY
# ═══════════════════════════════════════════════════════
@bot.tree.command(name="panel-weryfikacji", description="Wyślij panel weryfikacji")
@commands.has_permissions(administrator=True)
async def panel_weryfikacji(interaction: discord.Interaction):
    channel = bot.get_channel(KANAL_WERYFIKACJI)
    if not channel:
        await interaction.response.send_message("❌ Brak kanału", ephemeral=True)
        return
    await wyslij_panel_weryfikacji(channel)
    await interaction.response.send_message("✅ Panel wysłany", ephemeral=True)

@bot.tree.command(name="ogloszenie-rp", description="Wyślij ogłoszenie sesji RP")
@app_commands.describe(czas="Czas rozpoczęcia", kod="Kod do serwera", organizator="Organizator", max_graczy="Max graczy")
async def ogloszenie_rp(interaction: discord.Interaction, czas: str, kod: str, organizator: str, max_graczy: int = 0):
    if not ma_role(interaction.user, ROLA_OGLOSZENIA_RP):
        await interaction.response.send_message("❌ Brak uprawnień", ephemeral=True)
        return

    channel = bot.get_channel(KANAL_OGLOSZENIA_RP)
    if not channel:
        await interaction.response.send_message("❌ Brak kanału ogłoszeń", ephemeral=True)
        return

    embed = discord.Embed(
        title="📢 Zaplanowano Sesję Roleplay!!!",
        description=f"**Czas rozpoczęcia:** {czas}\n**Organizator:** {organizator}\n**Kod do serwera:** `{kod}`\n**Gracze:** ---/{max_graczy if max_graczy > 0 else '---'}",
        color=0x5865F2
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")
    embed.set_footer(text=f"Made by {interaction.user.display_name} • Dzisiaj {datetime.now().strftime('%H:%M')}")

    await channel.send(embed=embed)
    await interaction.response.send_message("✅ Ogłoszenie wysłane", ephemeral=True)

@bot.tree.command(name="dowod", description="Wyrób dowód osobisty")
@app_commands.describe(numer_postaci="Postać", imie_nazwisko="Imię i nazwisko", data_urodzenia="DD.MM.RRRR", obywatelstwo="Obywatelstwo")
@app_commands.choices(numer_postaci=[app_commands.Choice(name="Postać 1", value=1), app_commands.Choice(name="Postać 2", value=2)])
async def dowod(interaction: discord.Interaction, numer_postaci: app_commands.Choice[int], imie_nazwisko: str, data_urodzenia: str, obywatelstwo: str):
    if not ma_role(interaction.user, ROLA_DOWOD):
        await interaction.response.send_message("❌ Brak uprawnień", ephemeral=True); return
    dane = await pobierz_dane_roblox(interaction.user.id)
    if not dane:
        await interaction.response.send_message("❌ Zweryfikuj się przez Roblox", ephemeral=True); return
    roblox_id, roblox_username = dane

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dowody WHERE discord_id = ? AND numer_postaci = ?", (interaction.user.id, numer_postaci.value))
    if cursor.fetchone():
        conn.close()
        await interaction.response.send_message(f"❌ Masz już dowód Postaci {numer_postaci.value}", ephemeral=True); return

    avatar_url = None
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={roblox_id}&size=420x420&format=Png") as resp:
            data = await resp.json()
            if data.get("data"): avatar_url = data["data"][0]["imageUrl"]

    cursor.execute("INSERT INTO dowody (discord_id, numer_postaci, imie_nazwisko, data_urodzenia, obywatelstwo, ssn, roblox_username, roblox_avatar) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (interaction.user.id, numer_postaci.value, imie_nazwisko, data_urodzenia, obywatelstwo, roblox_id, roblox_username, avatar_url))
    conn.commit()
    conn.close()

    channel = bot.get_channel(KANAL_DOWODY)
    if channel:
        embed = discord.Embed(title=f"🪪 Dowód - Postać {numer_postaci.value}", color=0x3498DB)
        embed.add_field(name="Imię i nazwisko", value=imie_nazwisko, inline=False)
        embed.add_field(name="Data urodzenia", value=data_urodzenia, inline=False)
        embed.add_field(name="Obywatelstwo", value=obywatelstwo, inline=False)
        embed.add_field(name="SSN", value=str(roblox_id), inline=False)
        embed.add_field(name="Nick", value=roblox_username, inline=False)
        embed.set_thumbnail(url=avatar_url or interaction.user.display_avatar.url)
        embed.set_footer(text=f"Wydano: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        await channel.send(embed=embed)

    await interaction.response.send_message(f"✅ Dowód Postaci {numer_postaci.value} wydany", ephemeral=True)

@bot.tree.command(name="wystaw-wyrok", description="Wystaw wyrok")
@app_commands.describe(osoba="Osoba", kara_wiezienia="Kara więzienia", kwota="Kwota", zarzuty="Zarzuty")
async def wystaw_wyrok(interaction: discord.Interaction, osoba: discord.Member, kara_wiezienia: str, kwota: str, zarzuty: str):
    if not ma_role(interaction.user, ROLA_POLICJA):
        await interaction.response.send_message("❌ Brak uprawnień", ephemeral=True); return
    dane = await pobierz_dane_roblox(osoba.id)
    if not dane:
        await interaction.response.send_message("❌ Osoba niezweryfikowana", ephemeral=True); return
    roblox_id, roblox_username = dane
    data = datetime.now().strftime("%d.%m.%Y %H:%M")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO wyroki (osoba_id, osoba_nick, funkcjonariusz, kara_wiezienia, kwota, zarzuty, data) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (osoba.id, osoba.display_name, interaction.user.display_name, kara_wiezienia, kwota, zarzuty, data))
    conn.commit()
    conn.close()

    channel = bot.get_channel(KANAL_WYROKI)
    if channel:
        embed = discord.Embed(title="⚖️ Wyrok", color=0xE74C3C)
        embed.add_field(name="Osoba", value=osoba.mention, inline=False)
        embed.add_field(name="Nick Roblox", value=roblox_username, inline=False)
        embed.add_field(name="SSN", value=str(roblox_id), inline=False)
        embed.add_field(name="Kara", value=kara_wiezienia, inline=False)
        embed.add_field(name="Kwota", value=kwota, inline=False)
        embed.add_field(name="Zarzuty", value=zarzuty, inline=False)
        embed.add_field(name="Data", value=data, inline=False)
        embed.add_field(name="Funkcjonariusz", value=interaction.user.mention, inline=False)
        await channel.send(embed=embed)
    await interaction.response.send_message("✅ Wyrok wystawiony", ephemeral=True)

@bot.tree.command(name="wystaw-mandat", description="Wystaw mandat")
@app_commands.describe(osoba="Osoba", kwota="Kwota", zarzuty="Zarzuty")
async def wystaw_mandat(interaction: discord.Interaction, osoba: discord.Member, kwota: str, zarzuty: str):
    if not ma_role(interaction.user, ROLA_POLICJA):
        await interaction.response.send_message("❌ Brak uprawnień", ephemeral=True); return
    dane = await pobierz_dane_roblox(osoba.id)
    if not dane:
        await interaction.response.send_message("❌ Osoba niezweryfikowana", ephemeral=True); return
    roblox_id, roblox_username = dane
    data = datetime.now().strftime("%d.%m.%Y %H:%M")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO mandaty (osoba_id, osoba_nick, funkcjonariusz, kwota, zarzuty, data) VALUES (?, ?, ?, ?, ?, ?)",
                   (osoba.id, osoba.display_name, interaction.user.display_name, kwota, zarzuty, data))
    conn.commit()
    conn.close()

    channel = bot.get_channel(KANAL_MANDATY)
    if channel:
        embed = discord.Embed(title="📋 Mandat", color=0xF39C12)
        embed.add_field(name="Osoba", value=osoba.mention, inline=False)
        embed.add_field(name="Nick Roblox", value=roblox_username, inline=False)
        embed.add_field(name="SSN", value=str(roblox_id), inline=False)
        embed.add_field(name="Kwota", value=kwota, inline=False)
        embed.add_field(name="Zarzuty", value=zarzuty, inline=False)
        embed.add_field(name="Data", value=data, inline=False)
        embed.add_field(name="Funkcjonariusz", value=interaction.user.mention, inline=False)
        await channel.send(embed=embed)
    await interaction.response.send_message("✅ Mandat wystawiony", ephemeral=True)

@bot.tree.command(name="wystaw-fakture", description="Wystaw fakturę")
@app_commands.describe(komu="Komu", za_co="Za co", dzien="Dzień", kwota="Kwota")
async def wystaw_fakture(interaction: discord.Interaction, komu: discord.Member, za_co: str, dzien: str, kwota: str):
    if not ma_role(interaction.user, ROLA_FAKTURY):
        await interaction.response.send_message("❌ Brak uprawnień", ephemeral=True); return
    channel = bot.get_channel(KANAL_FAKTURY)
    if channel:
        embed = discord.Embed(title="📄 Faktura", color=0x9B59B6)
        embed.add_field(name="Kto", value=interaction.user.mention, inline=False)
        embed.add_field(name="Komu", value=komu.mention, inline=False)
        embed.add_field(name="Za co", value=za_co, inline=False)
        embed.add_field(name="Dzień", value=dzien, inline=False)
        embed.add_field(name="Kwota", value=kwota, inline=False)
        await channel.send(embed=embed)
    await interaction.response.send_message("✅ Faktura wystawiona", ephemeral=True)

@bot.tree.command(name="wystaw-list-gonczy", description="Wystaw list gończy")
@app_commands.describe(kto="Kto", na_kogo="Na kogo", powod="Powód", priorytet="Priorytet")
@app_commands.choices(priorytet=[app_commands.Choice(name="Tak", value="Tak"), app_commands.Choice(name="Nie", value="Nie")])
async def wystaw_list_gonczy(interaction: discord.Interaction, kto: str, na_kogo: str, powod: str, priorytet: app_commands.Choice[str]):
    if not ma_role(interaction.user, ROLA_LISTY_GONCZE):
        await interaction.response.send_message("❌ Brak uprawnień", ephemeral=True); return
    channel = bot.get_channel(KANAL_LISTY_GONCZE)
    if channel:
        color = 0xFF0000 if priorytet.value == "Tak" else 0xE67E22
        embed = discord.Embed(title="🔴 LIST GOŃCZY", color=color)
        embed.add_field(name="Kto", value=kto, inline=False)
        embed.add_field(name="Na kogo", value=na_kogo, inline=False)
        embed.add_field(name="Powód", value=powod, inline=False)
        embed.add_field(name="Priorytet", value=priorytet.value, inline=False)
        await channel.send(embed=embed)
    await interaction.response.send_message("✅ List gończy wystawiony", ephemeral=True)

@bot.tree.command(name="rejestruj-pojazd", description="Zarejestruj pojazd")
@app_commands.describe(nr="Numer rejestracyjny", marka="Marka/Model", wlasciciel="Właściciel")
async def rejestruj_pojazd(interaction: discord.Interaction, nr: str, marka: str, wlasciciel: discord.Member):
    if not ma_role(interaction.user, ROLA_REJESTRACJA):
        await interaction.response.send_message("❌ Brak uprawnień", ephemeral=True); return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rejestracje WHERE nr_rejestracyjny = ?", (nr,))
    if cursor.fetchone():
        conn.close()
        await interaction.response.send_message("❌ Numer zajęty", ephemeral=True); return
    cursor.execute("INSERT INTO rejestracje (nr_rejestracyjny, marka_model, wlasciciel_id, wlasciciel_nick) VALUES (?, ?, ?, ?)",
                   (nr, marka, wlasciciel.id, wlasciciel.display_name))
    conn.commit()
    conn.close()
    channel = bot.get_channel(KANAL_REJESTRACJA)
    if channel:
        embed = discord.Embed(title="🚗 Rejestracja", color=0x2ECC71)
        embed.add_field(name="Nr", value=nr, inline=False)
        embed.add_field(name="Marka/Model", value=marka, inline=False)
        embed.add_field(name="Właściciel", value=wlasciciel.mention, inline=False)
        embed.add_field(name="Podpis", value="Urząd Miasta Skierniewice", inline=False)
        await channel.send(embed=embed)
    await interaction.response.send_message("✅ Pojazd zarejestrowany", ephemeral=True)

@bot.tree.command(name="reset-weryfikacji", description="Zresetuj weryfikację użytkownika")
@app_commands.describe(osoba="Osoba")
@commands.has_permissions(administrator=True)
async def reset_weryfikacji(interaction: discord.Interaction, osoba: discord.Member):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT roblox_username FROM weryfikacje WHERE discord_id = ?", (osoba.id,))
    wynik = cursor.fetchone()
    if not wynik:
        conn.close()
        await interaction.response.send_message(f"❌ {osoba.mention} niezweryfikowany", ephemeral=True); return
    roblox_username = wynik[0]
    cursor.execute("DELETE FROM weryfikacje WHERE discord_id = ?", (osoba.id,))
    cursor.execute("DELETE FROM kody_weryfikacyjne WHERE discord_id = ?", (osoba.id,))
    conn.commit()
    conn.close()
    rola = interaction.guild.get_role(ROLA_WERYFIKOWANY)
    if rola and rola in osoba.roles: await osoba.remove_roles(rola)
    try: await osoba.edit(nick=None)
    except: pass
    await interaction.response.send_message(f"✅ Weryfikacja {osoba.mention} (`{roblox_username}`) zresetowana", ephemeral=True)

# ═══════════════════════════════════════════════════════
# START
# ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    init_db()
    bot.run(BOT_TOKEN)
