import sqlite3
import os

from config import DB_PATH

def init_db():
    """Tworzy wszystkie tabele w bazie danych"""

    # Upewnij sie ze folder istnieje (dla Railway Volume /data)
    folder = os.path.dirname(DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # TABELA 1: WERYFIKACJE ROBLOX
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weryfikacje (
            discord_id INTEGER PRIMARY KEY,
            roblox_id INTEGER,
            roblox_username TEXT,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # TABELA 2: KODY WERYFIKACYJNE (tymczasowe)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kody_weryfikacyjne (
            discord_id INTEGER PRIMARY KEY,
            kod TEXT,
            roblox_id INTEGER,
            roblox_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # TABELA 3: DOWODY OSOBISTE (max 2 na gracza)
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

    # TABELA 4: WYROKI
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

    # TABELA 5: MANDATY
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

    # TABELA 6: FAKTURY
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

    # TABELA 7: LISTY GONCZE
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

    # TABELA 8: REJESTRACJE POJAZDOW
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

    # TABELA 9: PODANIA (z message_id)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS podania (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id INTEGER,
            discord_username TEXT,
            frakcja TEXT,
            frakcja_nazwa TEXT,
            odpowiedzi TEXT,
            status TEXT DEFAULT 'oczekujace',
            timestamp TEXT,
            message_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # TABELA 10: STATUS PODAN (do akceptacji/odrzucenia)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS podania_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            podanie_id INTEGER,
            discord_id INTEGER,
            frakcja TEXT,
            status TEXT DEFAULT 'oczekujace',
            message_id TEXT,
            reviewed_by TEXT,
            reviewed_at TIMESTAMP,
            FOREIGN KEY (podanie_id) REFERENCES podania(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Baza danych gotowa!")

def get_db():
    """Zwraca polaczenie do bazy"""
    return sqlite3.connect(DB_PATH)
