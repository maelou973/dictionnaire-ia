from datetime import datetime
import requests
from bs4 import BeautifulSoup
from database import cur, conn

NOM = "Antonyme"

def telecharger_sources_antonyme(mot):

    url = f"https://www.antonyme.org/antonyme/{mot}"

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

        bloc = soup.select_one("#main-container > div.main-content > div.fiche > ul.synos")

        if bloc:
            existe = True
            contenu = str(bloc)
        else:
            existe = False
            contenu = ""

    cur.execute("""
        DELETE FROM sources_brutes
        WHERE mot=? AND langue=? AND source=?
    """, (mot, "fr", "Antonyme"))

    cur.execute("""
        INSERT INTO sources_brutes
        (mot, langue, source, url, existe, contenu_brut, date_recuperation)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        mot,
        "fr",
        "Antonyme",
        url,
        1 if existe else 0,
        contenu,
        datetime.now().strftime("%d/%m/%Y %H:%M")
    ))

    conn.commit()

    print("Antonyme:", "✅" if existe else "❌")

def telecharger(mot):
    telecharger_sources_antonyme(mot)