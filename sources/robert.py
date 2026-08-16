from datetime import datetime
import requests
from bs4 import BeautifulSoup
from database import cur, conn

NOM = "Le Robert"

def telecharger_sources_robert(mot):

    url = f"https://dictionnaire.lerobert.com/definition/{mot}"

    r = requests.get(
        url,
        headers={
            "User-Agent": "DictionnaireIA/0.1"
        }
    )

    if r.status_code != 200:
        existe = False
        contenu = ""
    else:
        soup = BeautifulSoup(r.text, "html.parser")

        bloc = soup.select_one("body > div.ws-c > main")

        if bloc:
            existe = True
            contenu = str(bloc)
        else:
            existe = False
            contenu = ""

    cur.execute("""
        DELETE FROM sources_brutes
        WHERE mot=? AND langue=? AND source=?
    """, (mot, "fr", "Le Robert"))

    cur.execute("""
        INSERT INTO sources_brutes
        (mot, langue, source, url, existe, contenu_brut, date_recuperation)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        mot,
        "fr",
        "Le Robert",
        url,
        1 if existe else 0,
        contenu,
        datetime.now().strftime("%d/%m/%Y %H:%M")
    ))

    conn.commit()

    print("Le Robert:", "✅" if existe else "❌")

def telecharger(mot):
    telecharger_sources_robert(mot)