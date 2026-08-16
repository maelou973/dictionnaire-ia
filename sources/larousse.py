from datetime import datetime
import requests
from bs4 import BeautifulSoup
from database import cur, conn

NOM = "Larousse"

def telecharger_sources_larousse(mot):
    url = f"https://www.larousse.fr/dictionnaires/francais/{mot}"

    r = requests.get(url, headers={
        "User-Agent": "DictionnaireIA/0.1"
    })

    if r.status_code != 200:
        existe = False
        contenu = ""
        url_finale = url
    else:
        url_finale = r.url
        soup = BeautifulSoup(r.text, "html.parser")

        bloc = soup.select_one("body > div.page > div.wrapper")

        if bloc:
            existe = True
            contenu = str(bloc)
        else:
            existe = False
            contenu = ""

    cur.execute("""
    DELETE FROM sources_brutes
    WHERE mot = ? AND langue = ? AND source = ?
    """, (mot, "fr", NOM))

    cur.execute("""
    INSERT INTO sources_brutes
    (mot, langue, source, url, existe, contenu_brut, date_recuperation)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        mot,
        "fr",
        NOM,
        url_finale,
        1 if existe else 0,
        contenu,
        datetime.now().strftime("%d/%m/%Y %H:%M")
    ))

    conn.commit()

    print(f"{NOM}:", "✅" if existe else "❌")

def telecharger(mot):
    telecharger_sources_larousse(mot)