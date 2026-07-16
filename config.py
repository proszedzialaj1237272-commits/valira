import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# Kanaly
KANAL_WERYFIKACJI = int(os.getenv("KANAL_WERYFIKACJI", "0"))
KANAL_DOWODY = int(os.getenv("KANAL_DOWODY", "0"))
KANAL_WYROKI = int(os.getenv("KANAL_WYROKI", "0"))
KANAL_MANDATY = int(os.getenv("KANAL_MANDATY", "0"))
KANAL_FAKTURY = int(os.getenv("KANAL_FAKTURY", "0"))
KANAL_LISTY_GONCZE = int(os.getenv("KANAL_LISTY_GONCZE", "0"))
KANAL_REJESTRACJA = int(os.getenv("KANAL_REJESTRACJA", "0"))
KANAL_OGLOSZENIA_RP = int(os.getenv("KANAL_OGLOSZENIA_RP", "0"))

# Kanaly podan (kazda frakcja osobno)
KANAL_PODANIA_KMP = int(os.getenv("KANAL_PODANIA_KMP", "0"))
KANAL_PODANIA_SPD = int(os.getenv("KANAL_PODANIA_SPD", "0"))
KANAL_PODANIA_JRG = int(os.getenv("KANAL_PODANIA_JRG", "0"))
KANAL_PODANIA_RSPR = int(os.getenv("KANAL_PODANIA_RSPR", "0"))

# Role
ROLA_WERYFIKOWANY = int(os.getenv("ROLA_WERYFIKOWANY", "0"))
ROLA_POLICJA = int(os.getenv("ROLA_POLICJA", "0"))
ROLA_FAKTURY = int(os.getenv("ROLA_FAKTURY", "0"))
ROLA_LISTY_GONCZE = int(os.getenv("ROLA_LISTY_GONCZE", "0"))
ROLA_REJESTRACJA = int(os.getenv("ROLA_REJESTRACJA", "0"))
ROLA_DOWOD = int(os.getenv("ROLA_DOWOD", "0"))
ROLA_OGLOSZENIA_RP = int(os.getenv("ROLA_OGLOSZENIA_RP", "0"))

DB_PATH = os.getenv("DB_PATH", "/data/bot_data.db")
