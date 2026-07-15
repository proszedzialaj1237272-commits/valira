import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import aiohttp
import asyncio
import os

from config import (
    BOT_TOKEN, GUILD_ID,
    KANAL_WERYFIKACJI, KANAL_DOWODY, KANAL_WYROKI,
    KANAL_MANDATY, KANAL_FAKTURY, KANAL_LISTY_GONCZE, KANAL_REJESTRACJA,
    ROLA_WERYFIKOWANY, ROLA_POLICJA, ROLA_FAKTURY,
    ROLA_LISTY_GONCZE, ROLA_REJESTRACJA, ROLA_DOWOD
)
from database import init_db, get_db

# ═══════════════════════════════════════════════════════
# USTAWIENIA BOTA
# ═══════════════════════════════════════════════════════
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ═══════════════════════════════════════════════════════
# POMOCNICZA FUNKCJA: Sprawdź czy użytkownik ma rolę
# ═══════════════════════════════════════════════════════
def ma_role(member: discord.Member, rola_id: int) -> bool:
    rola = member.guild.get_role(rola_id)
    if not rola:
        return False
    return rola in member.roles

# ═══════════════════════════════════════════════════════
# POMOCNICZA FUNKCJA: Pobierz dane Roblox użytkownika
# ═══════════════════════════════════════════════════════
async def pobierz_dane_roblox(discord_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT roblox_id, roblox_username FROM weryfikacje WHERE discord_id = ?", 
                   (discord_id,))
    wynik = cursor.fetchone()
    conn.close()
    return wynik  # (roblox_id, roblox_username) lub None

# ═══════════════════════════════════════════════════════
# START BOTA
# ═══════════════════════════════════════════════════════
@bot.event
async def on_ready():
    print(f"✅ Bot zalogowany jako: {bot.user}")
    print(f"🌐 Serwerów: {len(bot.guilds)}")
    
    # Synchronizacja komend slash
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synchronizowano {len(synced)} komend")
    except Exception as e:
        print(f"❌ Błąd sync: {e}")
    
    # Odtwórz panele po restarcie
    await odtworz_panel_weryfikacji()

# ═══════════════════════════════════════════════════════
# ODTWARZANIE PANELU PO RESTARCIE
# ═══════════════════════════════════════════════════════
async def odtworz_panel_weryfikacji():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, message_id FROM panele WHERE typ = 'weryfikacja'")
    panele = cursor.fetchall()
    conn.close()
    
    for panel in panele:
        channel_id, message_id = panel
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            continue
            
        channel = guild.get_channel(channel_id)
        if not channel:
            continue
            
        try:
            msg = await channel.fetch_message(message_id)
            print(f"✅ Panel odzyskany: {msg.id}")
        except discord.NotFound:
            print("⚠️ Panel usunięty, wysyłam nowy...")
            await wyslij_panel_weryfikacji(channel)

# ═══════════════════════════════════════════════════════
# WYŚLIJ PANEL WERYFIKACJI
# ═══════════════════════════════════════════════════════
async def wyslij_panel_weryfikacji(channel):
    embed = discord.Embed(
        title="🔐 Weryfikacja Roblox",
        description="Kliknij przycisk poniżej, aby zweryfikować konto Roblox.\n\n"
                    "Po weryfikacji otrzymasz:\n"
                    "• Zmianę nicku na nick z Roblox\n"
                    "• Rolę zweryfikowanego",
        color=0x00D4AA
    )
    embed.set_thumbnail(url="https://www.roblox.com/favicon.ico")
    
    view = WeryfikacjaView()
    msg = await channel.send(embed=embed, view=view)
    
    # Zapisz do bazy
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO panele (typ, channel_id, message_id) VALUES (?, ?, ?)",
        ("weryfikacja", channel.id, msg.id)
    )
    conn.commit()
    conn.close()
    
    return msg

# ═══════════════════════════════════════════════════════
# PRZYCISK WERYFIKACJI
# ═══════════════════════════════════════════════════════
class WeryfikacjaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Brak timeoutu — działa zawsze
    
    @discord.ui.button(label="Zweryfikuj się", style=discord.ButtonStyle.green, emoji="✅")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        # Sprawdź czy już zweryfikowany
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM weryfikacje WHERE discord_id = ?", (interaction.user.id,))
        if cursor.fetchone():
            conn.close()
            await interaction.response.send_message("✅ Już jesteś zweryfikowany!", ephemeral=True)
            return
        conn.close()
        
        # Otwórz okno do wpisania nicku
        await interaction.response.send_modal(WeryfikacjaModal())

# ═══════════════════════════════════════════════════════
# OKNO WERYFIKACJI (wpisujesz nick Roblox)
# ═══════════════════════════════════════════════════════
class WeryfikacjaModal(discord.ui.Modal, title="Weryfikacja Roblox"):
    roblox_nick = discord.ui.TextInput(
        label="Twój nick Roblox",
        placeholder="Wpisz DOKŁADNY nick z Roblox",
        required=True,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        nick = self.roblox_nick.value
        
        # Szukaj użytkownika w Roblox API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://users.roblox.com/v1/users/search?keyword={nick}&limit=10"
            ) as resp:
                if resp.status != 200:
                    await interaction.response.send_message(
                        "❌ Błąd połączenia z Roblox!", ephemeral=True
                    )
                    return
                
                data = await resp.json()
                users = data.get("data", [])
                
                # Znajdź DOKŁADNY nick
                user = None
                for u in users:
                    if u["name"].lower() == nick.lower():
                        user = u
                        break
                
                if not user:
                    await interaction.response.send_message(
                        f"❌ Nie znaleziono `{nick}` na Roblox!\n"
                        "Upewnij się, że wpisujesz DOKŁADNY nick.",
                        ephemeral=True
                    )
                    return
                
                roblox_id = user["id"]
                roblox_username = user["name"]
                
                # Pobierz avatar
                async with session.get(
                    f"https://thumbnails.roblox.com/v1/users/avatar-headshot?"
                    f"userIds={roblox_id}&size=420x420&format=Png"
                ) as av_resp:
                    av_data = await av_resp.json()
                    avatar_url = av_data["data"][0]["imageUrl"] if av_data.get("data") else None
        
        # Zapisz w bazie
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO weryfikacje (discord_id, roblox_id, roblox_username) VALUES (?, ?, ?)",
            (interaction.user.id, roblox_id, roblox_username)
        )
        conn.commit()
        conn.close()
        
        # Zmień nick na serwerze
        try:
            await interaction.user.edit(nick=roblox_username)
        except:
            pass  # Bot nie ma uprawnień
        
        # Dodaj rolę zweryfikowanego
        guild = interaction.guild
        rola = guild.get_role(ROLA_WERYFIKOWANY)
        if rola:
            await interaction.user.add_roles(rola)
        
        # Potwierdzenie
        embed = discord.Embed(
            title="✅ Weryfikacja udana!",
            description=f"**Nick:** {roblox_username}\n**ID:** {roblox_id}",
            color=0x00FF00
        )
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ═══════════════════════════════════════════════════════
# KOMENDA: /panel-weryfikacji (tylko dla adminów)
# ═══════════════════════════════════════════════════════
@bot.tree.command(name="panel-weryfikacji", description="Wyślij panel weryfikacji na kanał")
@commands.has_permissions(administrator=True)
async def panel_weryfikacji(interaction: discord.Interaction):
    channel = bot.get_channel(KANAL_WERYFIKACJI)
    if not channel:
        await interaction.response.send_message("❌ Kanał nie skonfigurowany!", ephemeral=True)
        return
    
    await wyslij_panel_weryfikacji(channel)
    await interaction.response.send_message("✅ Panel wysłany!", ephemeral=True)

# ═══════════════════════════════════════════════════════
# KOMENDA: /dowod — WYRABIANIE DOWODU (max 2 postacie)
# ═══════════════════════════════════════════════════════
@bot.tree.command(name="dowod", description="Wyrób dowód osobisty")
@app_commands.describe(
    numer_postaci="Wybierz postać",
    imie_nazwisko="Imię i nazwisko postaci",
    data_urodzenia="Data urodzenia (DD.MM.RRRR)",
    obywatelstwo="Obywatelstwo"
)
@app_commands.choices(numer_postaci=[
    app_commands.Choice(name="Postać 1", value=1),
    app_commands.Choice(name="Postać 2", value=2)
])
async def dowod(interaction: discord.Interaction,
                numer_postaci: app_commands.Choice[int],
                imie_nazwisko: str,
                data_urodzenia: str,
                obywatelstwo: str):
    
    # Sprawdź rolę
    if not ma_role(interaction.user, ROLA_DOWOD):
        await interaction.response.send_message("❌ Nie masz uprawnień!", ephemeral=True)
        return
    
    # Sprawdź czy zweryfikowany
    dane = await pobierz_dane_roblox(interaction.user.id)
    if not dane:
        await interaction.response.send_message(
            "❌ Najpierw zweryfikuj się przez Roblox!", ephemeral=True
        )
        return
    
    roblox_id, roblox_username = dane
    
    # Sprawdź czy już ma ten dowód
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM dowody WHERE discord_id = ? AND numer_postaci = ?",
        (interaction.user.id, numer_postaci.value)
    )
    if cursor.fetchone():
        conn.close()
        await interaction.response.send_message(
            f"❌ Masz już dowód dla Postaci {numer_postaci.value}!", ephemeral=True
        )
        return
    
    # Pobierz avatar
    avatar_url = None
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://thumbnails.roblox.com/v1/users/avatar-headshot?"
            f"userIds={roblox_id}&size=420x420&format=Png"
        ) as resp:
            data = await resp.json()
            if data.get("data"):
                avatar_url = data["data"][0]["imageUrl"]
    
    # Zapisz do bazy
    cursor.execute(
        """INSERT INTO dowody 
           (discord_id, numer_postaci, imie_nazwisko, data_urodzenia, 
            obywatelstwo, ssn, roblox_username, roblox_avatar)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (interaction.user.id, numer_postaci.value, imie_nazwisko,
         data_urodzenia, obywatelstwo, roblox_id, roblox_username, avatar_url)
    )
    conn.commit()
    conn.close()
    
    # Wyślij na kanał dowodów
    channel = bot.get_channel(KANAL_DOWODY)
    if channel:
        embed = discord.Embed(
            title=f"🪪 Dowód Osobisty — Postać {numer_postaci.value}",
            color=0x3498DB
        )
        embed.add_field(name="Imię i nazwisko:", value=imie_nazwisko, inline=False)
        embed.add_field(name="Data urodzenia:", value=data_urodzenia, inline=False)
        embed.add_field(name="Obywatelstwo:", value=obywatelstwo, inline=False)
        embed.add_field(name="SSN:", value=str(roblox_id), inline=False)
        embed.add_field(name="Nick gracza:", value=roblox_username, inline=False)
        embed.add_field(name="Numer postaci:", value=str(numer_postaci.value), inline=False)
        embed.set_thumbnail(url=avatar_url or interaction.user.display_avatar.url)
        embed.set_footer(text=f"Wydano: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        
        await channel.send(embed=embed)
    
    await interaction.response.send_message(
        f"✅ Dowód dla Postaci {numer_postaci.value} wydany!", ephemeral=True
    )

# ═══════════════════════════════════════════════════════
# KOMENDA: /wystaw-wyrok
# ═══════════════════════════════════════════════════════
@bot.tree.command(name="wystaw-wyrok", description="Wystaw wyrok sądowy")
@app_commands.describe(
    osoba="Osoba otrzymująca wyrok",
    kara_wiezienia="Kara więzienia",
    kwota="Kwota grzywny",
    zarzuty="Zarzuty"
)
async def wystaw_wyrok(interaction: discord.Interaction,
                       osoba: discord.Member,
                       kara_wiezienia: str,
                       kwota: str,
                       zarzuty: str):
    
    if not ma_role(interaction.user, ROLA_POLICJA):
        await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)
        return
    
    dane = await pobierz_dane_roblox(osoba.id)
    if not dane:
        await interaction.response.send_message("❌ Osoba niezweryfikowana!", ephemeral=True)
        return
    
    roblox_id, roblox_username = dane
    funkcjonariusz = interaction.user.display_name
    data = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # Zapisz
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO wyroki (osoba_id, osoba_nick, funkcjonariusz, 
           kara_wiezienia, kwota, zarzuty, data)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (osoba.id, osoba.display_name, funkcjonariusz, 
         kara_wiezienia, kwota, zarzuty, data)
    )
    conn.commit()
    conn.close()
    
    # Wyślij
    channel = bot.get_channel(KANAL_WYROKI)
    if channel:
        embed = discord.Embed(title="⚖️ Wyrok Sądowy", color=0xE74C3C)
        embed.add_field(name="Osoba:", value=osoba.mention, inline=False)
        embed.add_field(name="Nick Roblox:", value=roblox_username, inline=False)
        embed.add_field(name="SSN:", value=str(roblox_id), inline=False)
        embed.add_field(name="Imię i nazwisko:", value=funkcjonariusz, inline=False)
        embed.add_field(name="Kara więzienia:", value=kara_wiezienia, inline=False)
        embed.add_field(name="Kwota:", value=kwota, inline=False)
        embed.add_field(name="Zarzuty:", value=zarzuty, inline=False)
        embed.add_field(name="Data:", value=data, inline=False)
        embed.add_field(name="Funkcjonariusz:", value=interaction.user.mention, inline=False)
        
        await channel.send(embed=embed)
    
    await interaction.response.send_message("✅ Wyrok wystawiony!", ephemeral=True)

# ═══════════════════════════════════════════════════════
# KOMENDA: /wystaw-mandat
# ═══════════════════════════════════════════════════════
@bot.tree.command(name="wystaw-mandat", description="Wystaw mandat karny")
@app_commands.describe(
    osoba="Osoba otrzymująca mandat",
    kwota="Kwota mandatu",
    zarzuty="Zarzuty"
)
async def wystaw_mandat(interaction: discord.Interaction,
                        osoba: discord.Member,
                        kwota: str,
                        zarzuty: str):
    
    if not ma_role(interaction.user, ROLA_POLICJA):
        await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)
        return
    
    dane = await pobierz_dane_roblox(osoba.id)
    if not dane:
        await interaction.response.send_message("❌ Osoba niezweryfikowana!", ephemeral=True)
        return
    
    roblox_id, roblox_username = dane
    funkcjonariusz = interaction.user.display_name
    data = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO mandaty (osoba_id, osoba_nick, funkcjonariusz, kwota, zarzuty, data) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (osoba.id, osoba.display_name, funkcjonariusz, kwota, zarzuty, data)
    )
    conn.commit()
    conn.close()
    
    channel = bot.get_channel(KANAL_MANDATY)
    if channel:
        embed = discord.Embed(title="📋 Mandat Karny", color=0xF39C12)
        embed.add_field(name="Osoba:", value=osoba.mention, inline=False)
        embed.add_field(name="Nick Roblox:", value=roblox_username, inline=False)
        embed.add_field(name="SSN:", value=str(roblox_id), inline=False)
        embed.add_field(name="Imię i nazwisko:", value=funkcjonariusz, inline=False)
        embed.add_field(name="Kwota:", value=kwota, inline=False)
        embed.add_field(name="Zarzuty:", value=zarzuty, inline=False)
        embed.add_field(name="Data:", value=data, inline=False)
        embed.add_field(name="Funkcjonariusz:", value=interaction.user.mention, inline=False)
        
        await channel.send(embed=embed)
    
    await interaction.response.send_message("✅ Mandat wystawiony!", ephemeral=True)

# ═══════════════════════════════════════════════════════
# KOMENDA: /wystaw-fakture
# ═══════════════════════════════════════════════════════
@bot.tree.command(name="wystaw-fakture", description="Wystaw fakturę")
@app_commands.describe(
    komu="Komu wystawiasz",
    za_co="Za co",
    dzien="Jakiego dnia",
    kwota="Kwota"
)
async def wystaw_fakture(interaction: discord.Interaction,
                         komu: discord.Member,
                         za_co: str,
                         dzien: str,
                         kwota: str):
    
    if not ma_role(interaction.user, ROLA_FAKTURY):
        await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)
        return
    
    channel = bot.get_channel(KANAL_FAKTURY)
    if channel:
        embed = discord.Embed(title="📄 Faktura", color=0x9B59B6)
        embed.add_field(name="Kto wystawia:", value=interaction.user.mention, inline=False)
        embed.add_field(name="Komu:", value=komu.mention, inline=False)
        embed.add_field(name="Za co:", value=za_co, inline=False)
        embed.add_field(name="Jakiego dnia:", value=dzien, inline=False)
        embed.add_field(name="Kwota:", value=kwota, inline=False)
        embed.add_field(name="Podpis:", value=interaction.user.mention, inline=False)
        
        await channel.send(embed=embed)
    
    await interaction.response.send_message("✅ Faktura wystawiona!", ephemeral=True)

# ═══════════════════════════════════════════════════════
# KOMENDA: /wystaw-list-gonczy
# ═══════════════════════════════════════════════════════
@bot.tree.command(name="wystaw-list-gonczy", description="Wystaw list gończy")
@app_commands.describe(
    kto="Kto wystawia",
    na_kogo="Na kogo",
    powod="Z jakiego powodu",
    priorytet="Priorytetowy?"
)
@app_commands.choices(priorytet=[
    app_commands.Choice(name="Tak", value="Tak"),
    app_commands.Choice(name="Nie", value="Nie")
])
async def wystaw_list_gonczy(interaction: discord.Interaction,
                              kto: str,
                              na_kogo: str,
                              powod: str,
                              priorytet: app_commands.Choice[str]):
    
    if not ma_role(interaction.user, ROLA_LISTY_GONCZE):
        await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)
        return
    
    channel = bot.get_channel(KANAL_LISTY_GONCZE)
    if channel:
        color = 0xFF0000 if priorytet.value == "Tak" else 0xE67E22
        embed = discord.Embed(title="🔴 LIST GOŃCZY", color=color)
        embed.add_field(name="Kto:", value=kto, inline=False)
        embed.add_field(name="Na kogo:", value=na_kogo, inline=False)
        embed.add_field(name="Powód:", value=powod, inline=False)
        embed.add_field(name="Priorytet:", value=priorytet.value, inline=False)
        
        await channel.send(embed=embed)
    
    await interaction.response.send_message("✅ List gończy wystawiony!", ephemeral=True)

# ═══════════════════════════════════════════════════════
# KOMENDA: /rejestruj-pojazd
# ═══════════════════════════════════════════════════════
@bot.tree.command(name="rejestruj-pojazd", description="Zarejestruj pojazd")
@app_commands.describe(
    nr_rejestracyjny="Numer rejestracyjny",
    marka_model="Marka i model",
    wlasciciel="Właściciel"
)
async def rejestruj_pojazd(interaction: discord.Interaction,
                            nr_rejestracyjny: str,
                            marka_model: str,
                            wlasciciel: discord.Member):
    
    if not ma_role(interaction.user, ROLA_REJESTRACJA):
        await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)
        return
    
    # Sprawdź czy numer już istnieje
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rejestracje WHERE nr_rejestracyjny = ?", (nr_rejestracyjny,))
    if cursor.fetchone():
        conn.close()
        await interaction.response.send_message(
            "❌ Ten numer już istnieje!", ephemeral=True
        )
        return
    
    cursor.execute(
        "INSERT INTO rejestracje (nr_rejestracyjny, marka_model, wlasciciel_id, wlasciciel_nick) "
        "VALUES (?, ?, ?, ?)",
        (nr_rejestracyjny, marka_model, wlasciciel.id, wlasciciel.display_name)
    )
    conn.commit()
    conn.close()
    
    channel = bot.get_channel(KANAL_REJESTRACJA)
    if channel:
        embed = discord.Embed(title="🚗 Rejestracja Pojazdu", color=0x2ECC71)
        embed.add_field(name="Nr rejestracyjny:", value=nr_rejestracyjny, inline=False)
        embed.add_field(name="Marka / Model:", value=marka_model, inline=False)
        embed.add_field(name="Właściciel:", value=wlasciciel.mention, inline=False)
        embed.add_field(name="Podpis:", value="Urząd Miasta Warszawy", inline=False)
        
        await channel.send(embed=embed)
    
    await interaction.response.send_message("✅ Pojazd zarejestrowany!", ephemeral=True)

# ═══════════════════════════════════════════════════════
# URUCHOMIENIE BOTA
# ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    init_db()  # Stwórz bazę danych
    bot.run(BOT_TOKEN)