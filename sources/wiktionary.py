from datetime import datetime
import requests
from database import cur, conn

NOM = "Wiktionary"

def recuperer_wikicode(mot, langue):
    url_page = f"https://{langue}.wiktionary.org/wiki/{mot}"
    url_raw = f"https://{langue}.wiktionary.org/w/index.php"

    params = {
        "title": mot,
        "action": "raw"
    }

    r = requests.get(url_raw, params=params, headers={
        "User-Agent": "DictionnaireIA/0.1"
    })

    if r.status_code != 200:
        return False, url_page, ""

    texte = r.text.strip()

    if not texte:
        return False, url_page, ""

    if "There is currently no text in this page" in texte:
        return False, url_page, ""
    if "Il n’y a pour l’instant aucun texte sur cette page" in texte:
        return False, url_page, ""

    return True, url_page, texte


def recuperer_langues_wiktionary():
    url = "https://meta.wikimedia.org/w/api.php"

    params = {
        "action": "sitematrix",
        "format": "json"
    }

    r = requests.get(url, params=params, headers={
        "User-Agent": "DictionnaireIA/0.1"
    })

    data = r.json()
    langues = []

    for key, value in data["sitematrix"].items():
        if not key.isdigit():
            continue

        for site in value.get("site", []):
            url_site = site.get("url", "")

            if "wiktionary.org" in url_site:
                code = url_site.split("//")[1].split(".")[0]
                langues.append(code)

    return langues

def telecharger_sources_wiktionnaire(mot, langues_autorisees=None):
    mot = mot.lower().strip()
    langues_avec = []

    if langues_autorisees:
        langues = [
            langue.strip().lower()
            for langue in langues_autorisees
            if langue.strip()
        ]
        print(f"{len(langues)} Wiktionnaires demandés : {', '.join(langues)}")
    else:
        langues = recuperer_langues_wiktionary()
        print(f"{len(langues)} Wiktionnaires trouvés.")

    for langue in langues:
        existe, url, contenu = recuperer_wikicode(mot, langue)

        cur.execute("""
        DELETE FROM sources_brutes
        WHERE mot = ? AND langue = ? AND source = ?
        """, (mot, langue, NOM))

        cur.execute("""
        INSERT INTO sources_brutes
        (mot, langue, source, url, existe, contenu_brut, date_recuperation)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            mot,
            langue,
            NOM,
            url,
            1 if existe else 0,
            contenu if existe else "",
            datetime.now().strftime("%d/%m/%Y %H:%M")
        ))

        print(langue, "✅" if existe else "❌")

        if existe:
            langues_avec.append(langue)

    print(
        f"«{mot}» est trouvé dans {len(langues_avec)} langue(s) : "
        f"{', '.join(langues_avec) if langues_avec else 'aucune'}"
    )

    conn.commit()


def telecharger(mot, langues_autorisees=None):
    telecharger_sources_wiktionnaire(
        mot,
        langues_autorisees=langues_autorisees
    )