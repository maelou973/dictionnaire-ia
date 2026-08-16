from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
from database import cur, conn

NOM = "Académie française"
SOURCE = "Académie française"
LANGUE = "fr"
BASE_URL = "https://www.dictionnaire-academie.fr"


def creer_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    session.get(BASE_URL + "/")
    return session

def nom_edition_depuis_url(url):
    match = re.search(r"/article/A(\d)", url)

    if not match:
        return "édition inconnue"

    numero = int(match.group(1))

    if numero == 1:
        return "1re édition"

    return f"{numero}e édition"

def chercher_articles(mot, session):
    r = session.post(
        BASE_URL + "/search",
        data={
            "term": mot,
            "options": "1"
        },
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": BASE_URL + "/"
        }
    )

    if r.status_code != 200:
        return []

    try:
        data = r.json()
    except Exception:
        return []

    return data.get("result", [])


def url_absolue(href):
    if not href:
        return None

    if href.startswith("http"):
        return href

    return BASE_URL + href


def trouver_urls_editions(html, url_principale):
    soup = BeautifulSoup(html, "html.parser")

    urls = []

    # URL actuelle
    urls.append(url_principale)

    # Boutons/liens des anciennes éditions : v1, v2, ..., v9
    for i in range(1, 10):
        element = soup.select_one(f"#v{i}")

        if not element:
            continue

        href = element.get("href")

        if not href:
            lien = element.select_one("a")
            if lien:
                href = lien.get("href")

        url = url_absolue(href)

        if url and url not in urls:
            urls.append(url)

    return urls


def recuperer_page(session, url):
    r = session.get(url, headers={
        "Referer": BASE_URL + "/"
    })

    if r.status_code != 200:
        return False, ""

    return True, r.text


def extraire_contenu(html):
    soup = BeautifulSoup(html, "html.parser")
    bloc = soup.select_one("#contenu")

    if not bloc:
        return None

    return str(bloc)


def fabriquer_bloc_edition(url, html):
    contenu = extraire_contenu(html)

    if not contenu:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    titre = ""
    h1 = soup.select_one("h1")
    if h1:
        titre = h1.get_text(" ", strip=True)

    edition = ""
    texte_page = soup.get_text(" ", strip=True)

    for morceau in texte_page.split():
        if "édition" in morceau.lower():
            edition = morceau
            break

    return f"""
<!-- ================================================== -->
<!-- SOURCE : {SOURCE} -->
<!-- URL : {url} -->
<!-- TITRE : {titre} -->
<!-- ================================================== -->

{contenu}

"""


def telecharger(mot):
    session = creer_session()

    resultats = chercher_articles(mot, session)

    cur.execute("""
    DELETE FROM sources_brutes
    WHERE mot = ? AND langue = ? AND source = ?
    """, (mot, LANGUE, SOURCE))

    if not resultats:
        cur.execute("""
        INSERT INTO sources_brutes
        (mot, langue, source, url, existe, contenu_brut, date_recuperation, page_titre, page_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mot,
            LANGUE,
            SOURCE,
            BASE_URL + "/search",
            0,
            "",
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            None,
            "recherche"
        ))

        conn.commit()
        print(f"{NOM}: ❌")
        return

    meilleur = resultats[0]
    url_principale = meilleur.get("url", "")

    ok, html_principal = recuperer_page(session, url_principale)

    if not ok:
        conn.commit()
        print(f"{NOM}: ❌")
        return

    urls_editions = trouver_urls_editions(html_principal, url_principale)

    nombre_insertions = 0

    for url in urls_editions:
        ok_page, html = recuperer_page(session, url)

        if not ok_page:
            continue

        bloc = fabriquer_bloc_edition(url, html)

        if not bloc:
            continue

        edition = nom_edition_depuis_url(url)

        entete = f"""
<!--
Source : {SOURCE}
Mot recherché : {mot}
Résultat choisi : {meilleur.get("label", "")}
Nature : {meilleur.get("nature", "")}
Homographe : {meilleur.get("nbhomograph", "")}
Score : {meilleur.get("score", "")}
Édition : {edition}
URL : {url}
-->
"""

        contenu_final = entete + "\n" + bloc

        cur.execute("""
        INSERT INTO sources_brutes
        (mot, langue, source, url, existe, contenu_brut, date_recuperation, page_titre, page_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mot,
            LANGUE,
            SOURCE,
            url,
            1,
            contenu_final,
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            edition,
            "edition"
        ))

        nombre_insertions += 1

    conn.commit()

    print(f"{NOM}: {'✅' if nombre_insertions else '❌'}")
    if nombre_insertions:
        print(f"→ {meilleur.get('label', '')} | {nombre_insertions} édition(s)")