import os
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════
# TOKEN BOTA (z Discord Developer Portal)
# ═══════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "TU_WKLEJ_SWÓJ_TOKEN")

# ═══════════════════════════════════════
# ID TWOJEGO SERWERA DISCORD
# Jak znaleźć: Prawy przycisk na serwer → Kopiuj ID
# (musisz mieć włączony Tryb Dewelopera w Discord)
# ═══════════════════════════════════════
GUILD_ID = int(os.getenv("GUILD_ID", "TU_WKLEJ_ID_SERWERA"))

# ═══════════════════════════════════════
# ID KANAŁÓW (Prawy przycisk na kanał → Kopiuj ID)
# ═══════════════════════════════════════
KANAL_WERYFIKACJI = int(os.getenv("KANAL_WERYFIKACJI", "TU_ID_KANAŁU"))
KANAL_DOWODY      = int(os.getenv("KANAL_DOWODY",      "TU_ID_KANAŁU"))
KANAL_WYROKI      = int(os.getenv("KANAL_WYROKI",      "TU_ID_KANAŁU"))
KANAL_MANDATY     = int(os.getenv("KANAL_MANDATY",     "TU_ID_KANAŁU"))
KANAL_FAKTURY     = int(os.getenv("KANAL_FAKTURY",     "TU_ID_KANAŁU"))
KANAL_LISTY_GONCZE = int(os.getenv("KANAL_LISTY_GONCZE", "TU_ID_KANAŁU"))
KANAL_REJESTRACJA = int(os.getenv("KANAL_REJESTRACJA", "TU_ID_KANAŁU"))

# ═══════════════════════════════════════
# ID RÓL (Prawy przycisk na rolę → Kopiuj ID)
# ═══════════════════════════════════════
ROLA_WERYFIKOWANY = int(os.getenv("ROLA_WERYFIKOWANY", "TU_ID_ROLI"))
ROLA_POLICJA      = int(os.getenv("ROLA_POLICJA",      "TU_ID_ROLI"))
ROLA_FAKTURY      = int(os.getenv("ROLA_FAKTURY",      "TU_ID_ROLI"))
ROLA_LISTY_GONCZE = int(os.getenv("ROLA_LISTY_GONCZE", "TU_ID_ROLI"))
ROLA_REJESTRACJA  = int(os.getenv("ROLA_REJESTRACJA",  "TU_ID_ROLI"))
ROLA_DOWOD        = int(os.getenv("ROLA_DOWOD",        "TU_ID_ROLI"))

# ═══════════════════════════════════════
# ŚCIEŻKA DO BAZY DANYCH
# Na Railway: /data/bot_data.db (Volume)
# Lokalnie:   bot_data.db
# ═══════════════════════════════════════
DB_PATH = os.getenv("DB_PATH", "bot_data.db")