from datetime import datetime
import requests
from bs4 import BeautifulSoup
from database import cur, conn

NOM = "Littré"

def telecharger_sources_littre(mot):

    url = f"https://www.littre.org/definition/{mot}"

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

        bloc = soup.select_one("section.definition")

        if bloc:
            existe = True
            contenu = str(bloc)
        else:
            existe = False
            contenu = ""

    cur.execute("""
        DELETE FROM sources_brutes
        WHERE mot=? AND langue=? AND source=?
    """, (mot, "fr", "Littré"))

    cur.execute("""
        INSERT INTO sources_brutes
        (mot, langue, source, url, existe, contenu_brut, date_recuperation)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        mot,
        "fr",
        "Littré",
        url,
        1 if existe else 0,
        contenu,
        datetime.now().strftime("%d/%m/%Y %H:%M")
    ))

    conn.commit()

    print("Littré:", "✅" if existe else "❌")

def telecharger(mot):
    telecharger_sources_littre(mot)