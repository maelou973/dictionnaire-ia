from datetime import datetime
import json
import time
from urllib.parse import quote

import requests

from database import cur, conn


NOM = "Wikidata"

API_URL = "https://www.wikidata.org/w/api.php"

HEADERS = {
    "User-Agent": "DictionnaireIA/0.1"
}

# Nombre de résultats Wikidata à prendre PAR LANGUE.
NB_RESULTATS_PAR_LANGUE = 20

# Petite pause entre les requêtes.
# Si tu veux aller plus vite, baisse un peu.
# Si Wikimedia râle, augmente.
PAUSE_REQUETE = 1

# Pour tester sans lancer 300 langues, mets par exemple 10.
# Pour tout faire : None
# Pour mettre des langues précises, mets une liste de codes ISO 639-1 : ["fr", "en", "es"]
MAX_LANGUES = ["fr", "en", "es"]

# Plus c'est riche, plus c'est gros.
# Version riche :
PROPS_ENTITE = "labels|descriptions|aliases|claims|sitelinks"

# Version plus légère, si un jour tu veux calmer la bête :
# PROPS_ENTITE = "labels|descriptions|aliases|sitelinks"


session = requests.Session()
session.headers.update(HEADERS)


def appel_api(params):
    params = {
        "format": "json",
        "formatversion": "2",
        **params
    }

    for tentative in range(3):
        r = session.get(
            API_URL,
            params=params,
            timeout=30
        )

        if r.status_code == 429:
            attente = 2 + tentative * 3
            print(f"  ⚠️ Trop de requêtes, pause {attente}s...")
            time.sleep(attente)
            continue

        r.raise_for_status()
        data = r.json()

        if "error" in data:
            raise Exception(data["error"])

        return data

    raise Exception("Trop de requêtes après plusieurs tentatives.")


def recuperer_langues_wikidata():
    """
    Récupère les langues supportées par MediaWiki/Wikidata.
    Wikidata est un seul site multilingue : on ne cherche pas des sous-domaines,
    on change le paramètre language dans l'API.
    """
    # 1. Si MAX_LANGUES est une liste précise (ex: ["fr", "en"]), on la renvoie directement
    if isinstance(MAX_LANGUES, list):
        return MAX_LANGUES
    
    # 2. Sinon, on interroge l'API pour récupérer toutes les langues disponibles
    data = appel_api({
        "action": "query",
        "meta": "siteinfo",
        "siprop": "languages"
    })

    langues = []
    for langue in data.get("query", {}).get("languages", []):
        code = langue.get("code")
        if code:
            langues.append(code)

    langues = sorted(set(langues))

    # 3. Si MAX_LANGUES est un nombre, on ne garde que ce nombre de langues dans la liste
    if isinstance(MAX_LANGUES, int) or isinstance(MAX_LANGUES, float):
        langues = langues[:int(MAX_LANGUES)]

    return langues

def rechercher_wikidata(mot, langue):
    """
    Recherche le mot dans Wikidata, dans une langue donnée.
    """

    data = appel_api({
        "action": "wbsearchentities",
        "search": mot,
        "language": langue,
        "uselang": langue,
        "type": "item",
        "limit": NB_RESULTATS_PAR_LANGUE
    })

    return data.get("search", [])


def telecharger_entite(qid, langue):
    """
    Télécharge l'entité Wikidata.
    On garde la langue de recherche + français + anglais.
    Ça évite de perdre le contexte sans exploser complètement à chaque QID.
    """

    langues = f"{langue}|fr|en"

    data = appel_api({
        "action": "wbgetentities",
        "ids": qid,
        "props": PROPS_ENTITE,
        "languages": langues,
        "languagefallback": "1"
    })

    return data.get("entities", {}).get(qid)


def supprimer_anciennes_sources_wikidata(mot):
    cur.execute("""
        DELETE FROM sources_brutes
        WHERE mot = ? AND source = ?
    """, (mot, NOM))

    conn.commit()


def enregistrer_resultat(mot, langue, rang, resultat_recherche, entite):
    qid = resultat_recherche.get("id")
    label = resultat_recherche.get("label", "")
    description = resultat_recherche.get("description", "")

    url = f"https://www.wikidata.org/wiki/{qid}"

    page_titre = qid

    if label:
        page_titre += f" — {label}"

    contenu = {
        "mot_recherche": mot,
        "langue_recherche": langue,
        "rang_recherche": rang,
        "qid": qid,
        "resultat_recherche": resultat_recherche,
        "entite_wikidata": entite
    }

    contenu_brut = json.dumps(
        contenu,
        ensure_ascii=False,
        indent=2
    )

    cur.execute("""
        INSERT INTO sources_brutes
        (
            mot,
            langue,
            source,
            url,
            existe,
            contenu_brut,
            date_recuperation,
            page_titre,
            page_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        mot,
        langue,
        NOM,
        url,
        1,
        contenu_brut,
        datetime.now().strftime("%d/%m/%Y %H:%M"),
        page_titre,
        "wikidata_item"
    ))


def enregistrer_absence(mot, langue):
    url_recherche = (
        "https://www.wikidata.org/w/index.php?search="
        + quote(mot)
        + "&title=Special:Search"
    )

    cur.execute("""
        INSERT INTO sources_brutes
        (
            mot,
            langue,
            source,
            url,
            existe,
            contenu_brut,
            date_recuperation,
            page_titre,
            page_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        mot,
        langue,
        NOM,
        url_recherche,
        0,
        "",
        datetime.now().strftime("%d/%m/%Y %H:%M"),
        mot,
        "wikidata_search"
    ))


def telecharger_sources_wikidata(mot):
    supprimer_anciennes_sources_wikidata(mot)

    try:
        langues = recuperer_langues_wikidata()
    except Exception as e:
        print(f"Wikidata: ❌ impossible de récupérer les langues : {e}")
        return

    print(f"{len(langues)} langues Wikidata trouvées.")

    langues_avec_resultats = []
    total_resultats_ajoutes = 0

    for langue in langues:
        try:
            resultats = rechercher_wikidata(mot, langue)
            time.sleep(PAUSE_REQUETE)

        except Exception as e:
            print(f"{langue}: ❌ erreur recherche : {e}")
            enregistrer_absence(mot, langue)
            conn.commit()
            continue

        if not resultats:
            print(f"{langue}: ❌")
            enregistrer_absence(mot, langue)
            conn.commit()
            continue

        nb_langue = 0

        for rang, resultat in enumerate(resultats, start=1):
            qid = resultat.get("id")

            if not qid:
                continue

            try:
                entite = telecharger_entite(qid, langue)
                time.sleep(PAUSE_REQUETE)

                enregistrer_resultat(
                    mot=mot,
                    langue=langue,
                    rang=rang,
                    resultat_recherche=resultat,
                    entite=entite
                )

                nb_langue += 1
                total_resultats_ajoutes += 1

            except Exception as e:
                print(f"  {langue} | {qid}: ❌ erreur entité : {e}")

        conn.commit()

        if nb_langue > 0:
            langues_avec_resultats.append(langue)
            print(f"{langue}: ✅ {nb_langue} résultat(s) ajouté(s)")
        else:
            print(f"{langue}: ❌")
            enregistrer_absence(mot, langue)
            conn.commit()

    print()
    print(
        f"«{mot}» est trouvé dans {len(langues_avec_resultats)} langue(s) Wikidata."
    )
    print(
        f"{total_resultats_ajoutes} résultat(s) Wikidata ajouté(s) au total."
    )

    if langues_avec_resultats:
        print("Langues avec résultats :", ", ".join(langues_avec_resultats))


def telecharger(mot):
    telecharger_sources_wikidata(mot)