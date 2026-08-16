import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DONNEES_DIR = BASE_DIR / "donnees"

DONNEES_DIR.mkdir(exist_ok=True)

DEFINITIONS_DB = DONNEES_DIR / "definitions.db"
SOURCES_BRUTES_DB = DONNEES_DIR / "sources_brutes.db"

conn = sqlite3.connect(DEFINITIONS_DB, check_same_thread=False)
cur = conn.cursor()


def base_attachee(nom_base):
    cur.execute("PRAGMA database_list")
    bases = cur.fetchall()

    for base in bases:
        if base[1] == nom_base:
            return True

    return False


if not base_attachee("sources_db"):
    cur.execute(
        "ATTACH DATABASE ? AS sources_db",
        (str(SOURCES_BRUTES_DB),)
    )


def colonne_existe(base, table, colonne):
    cur.execute(f"PRAGMA {base}.table_info({table})")
    colonnes = [ligne[1] for ligne in cur.fetchall()]
    return colonne in colonnes


def ajouter_colonne_si_absente(base, table, colonne, type_sql):
    if not colonne_existe(base, table, colonne):
        cur.execute(f"ALTER TABLE {base}.{table} ADD COLUMN {colonne} {type_sql}")


def initialiser_db():
    # definitions.db
    cur.execute("""
    CREATE TABLE IF NOT EXISTS definitions (
        mot TEXT PRIMARY KEY,
        resume TEXT,
        sources TEXT,
        date_generation TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS generations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mot TEXT,
        style TEXT,
        longueur TEXT,
        requete_utilisateur TEXT,
        sources_choisies TEXT,
        categories_choisies TEXT,
        contenu TEXT,
        date_generation TEXT,
        filtres_sources TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_utilisateur TEXT UNIQUE NOT NULL,
        mot_de_passe_hash TEXT NOT NULL,
        date_creation TEXT NOT NULL,
        role TEXT DEFAULT 'utilisateur'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token_hash TEXT UNIQUE NOT NULL,
        date_creation TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES utilisateurs(id)
    )
    """)

    # sources_brutes.db
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sources_db.sources_brutes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mot TEXT,
        langue TEXT,
        source TEXT,
        url TEXT,
        existe INTEGER,
        contenu_brut TEXT,
        date_recuperation TEXT,
        page_titre TEXT,
        page_type TEXT
    )
    """)

    # Migrations au cas où
    ajouter_colonne_si_absente("sources_db", "sources_brutes", "page_titre", "TEXT")
    ajouter_colonne_si_absente("sources_db", "sources_brutes", "page_type", "TEXT")

    ajouter_colonne_si_absente("main", "utilisateurs", "identifiant_public", "TEXT")
    ajouter_colonne_si_absente("main", "utilisateurs", "email", "TEXT")

    ajouter_colonne_si_absente("main", "generations", "filtres_sources", "TEXT")
    ajouter_colonne_si_absente("main", "generations", "user_id", "INTEGER")
    ajouter_colonne_si_absente("main", "generations", "nom_utilisateur", "TEXT")

    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_utilisateurs_identifiant_public
    ON utilisateurs (identifiant_public)
    """)

    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_utilisateurs_email
    ON utilisateurs (email)
    """)

    # Index pour accélérer
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_generations_mot
    ON generations (mot)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS sources_db.idx_sources_brutes_mot_source
    ON sources_brutes (mot, source)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS sources_db.idx_sources_brutes_mot_source_langue
    ON sources_brutes (mot, source, langue)
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_utilisateurs_nom ON utilisateurs (nom_utilisateur)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions (token_hash)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_generations_user_id ON generations (user_id)")

    conn.commit()