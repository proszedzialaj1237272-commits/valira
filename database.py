import sqlite3
import os

# Ścieżka do bazy — import z config
from config import DB_PATH

def init_db():
    """Tworzy wszystkie tabele w bazie danych"""
    
    # Upewnij się że folder istnieje (dla Railway Volume /data)
    folder = os.path.dirname(DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # ═══ TABELA 1: WERYFIKACJE ROBLOX ═══
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weryfikacje (
            discord_id INTEGER PRIMARY KEY,
            roblox_id INTEGER,
            roblox_username TEXT,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ═══ TABELA 2: DOWODY OSOBISTE (max 2 na gracza) ═══
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dowody (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id INTEGER,
            numer_postaci INTEGER CHECK(numer_postaci IN (1, 2)),
            imie_nazwisko TEXT,
            data_urodzenia TEXT,
            obywatelstwo TEXT,
            ssn INTEGER,
            roblox_username TEXT,
            roblox_avatar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(discord_id, numer_postaci)
        )
    ''')
    
    # ═══ TABELA 3: WYROKI ═══
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wyroki (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            osoba_id INTEGER,
            osoba_nick TEXT,
            funkcjonariusz TEXT,
            kara_wiezienia TEXT,
            kwota TEXT,
            zarzuty TEXT,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ═══ TABELA 4: MANDATY ═══
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mandaty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            osoba_id INTEGER,
            osoba_nick TEXT,
            funkcjonariusz TEXT,
            kwota TEXT,
            zarzuty TEXT,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ═══ TABELA 5: FAKTURY ═══
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faktury (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wystawiajacy_id INTEGER,
            wystawiajacy_nick TEXT,
            odbiorca_id INTEGER,
            odbiorca_nick TEXT,
            za_co TEXT,
            dzien TEXT,
            kwota TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ═══ TABELA 6: LISTY GOŃCZE ═══
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listy_goncze (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kto TEXT,
            na_kogo TEXT,
            powod TEXT,
            priorytet TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ═══ TABELA 7: REJESTRACJE POJAZDÓW ═══
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rejestracje (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nr_rejestracyjny TEXT UNIQUE,
            marka_model TEXT,
            wlasciciel_id INTEGER,
            wlasciciel_nick TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ═══ TABELA 8: PANELE (do odtwarzania po restarcie) ═══
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS panele (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            typ TEXT,
            channel_id INTEGER,
            message_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Baza danych gotowa!")

def get_db():
    """Zwraca połączenie do bazy"""
    return sqlite3.connect(DB_PATH)