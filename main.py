from datetime import datetime
from database import cur, conn, initialiser_db
from bs4 import BeautifulSoup
from sources.informations_sources import INFORMATIONS_SOURCES

SOURCES_PAR_CLE = {
    cle: informations["module"]
    for cle, informations in INFORMATIONS_SOURCES.items()
}
SOURCES = list(SOURCES_PAR_CLE.values())

initialiser_db()

def source_existe_deja(mot, source_module):
    cur.execute("""
    SELECT COUNT(*)
    FROM sources_brutes
    WHERE mot = ?
      AND source = ?
      AND existe = 1
    """, (mot, source_module.NOM))

    return cur.fetchone()[0] > 0

_CACHE_OPTIONS_SOURCES = None

def langues_wiktionary_presentes(mot):
    cur.execute("""
    SELECT langue
    FROM sources_brutes
    WHERE mot = ?
      AND source = ?
      AND existe = 1
    """, (mot, wiktionary.NOM))

    return {ligne[0] for ligne in cur.fetchall()}


def editions_academie_presentes(mot):
    cur.execute("""
    SELECT page_titre
    FROM sources_brutes
    WHERE mot = ?
      AND source = ?
      AND existe = 1
    """, (mot, academie_fr.NOM))

    return {ligne[0] for ligne in cur.fetchall()}


def supprimer_wiktionary_langues(mot, langues):
    if not langues:
        cur.execute("""
        DELETE FROM sources_brutes
        WHERE mot = ? AND source = ?
        """, (mot, wiktionary.NOM))
        conn.commit()
        return

    placeholders = ",".join(["?"] * len(langues))

    cur.execute(f"""
    DELETE FROM sources_brutes
    WHERE mot = ?
      AND source = ?
      AND langue IN ({placeholders})
    """, [mot, wiktionary.NOM] + langues)

    conn.commit()

def options_sources():
    global _CACHE_OPTIONS_SOURCES

    if _CACHE_OPTIONS_SOURCES is not None:
        return _CACHE_OPTIONS_SOURCES

    try:
        langues_wiktionary = wiktionary.recuperer_langues_wiktionary()
        langues_wiktionary = sorted(set(langues_wiktionary))
    except Exception:
        langues_wiktionary = []

    editions_academie = [
        "1re édition",
        "2e édition",
        "3e édition",
        "4e édition",
        "5e édition",
        "6e édition",
        "7e édition",
        "8e édition",
        "9e édition"
    ]

    _CACHE_OPTIONS_SOURCES = {
        "wiktionary": {
            "langues": langues_wiktionary
        },
        "academie_fr": {
            "editions": editions_academie
        }
    }

    return _CACHE_OPTIONS_SOURCES

def supprimer_source_brute(mot, source_module):
    cur.execute("""
    DELETE FROM sources_brutes
    WHERE mot = ?
      AND source = ?
    """, (mot, source_module.NOM))

    conn.commit()

def telecharger_source_sans_casser(source_module, mot, **kwargs):
    try:
        source_module.telecharger(mot, **kwargs)
    except Exception as erreur:
        print(f"{source_module.NOM}: ❌ erreur : {type(erreur).__name__}: {erreur}")

def recuperer_sources_pour_generation(mot, sources_choisies, filtres_sources=None):
    mot = mot.lower().strip()

    if sources_choisies is None:
        sources_choisies = list(SOURCES_PAR_CLE.keys())

    elif isinstance(sources_choisies, str):
        sources_choisies = [
            source.strip()
            for source in sources_choisies.split(",")
            if source.strip()
        ]

    noms_sources = []

    for cle in sources_choisies:
        source_module = SOURCES_PAR_CLE.get(cle)
        if source_module:
            noms_sources.append(source_module.NOM)

    if not noms_sources:
        return []

    placeholders = ",".join(["?"] * len(noms_sources))

    cur.execute(f"""
    SELECT source, langue, url, contenu_brut, page_titre, page_type
    FROM sources_brutes
    WHERE mot = ?
    AND existe = 1
    AND source IN ({placeholders})
    ORDER BY source COLLATE NOCASE, page_titre COLLATE NOCASE, langue COLLATE NOCASE
    """, [mot] + noms_sources)

    lignes = cur.fetchall()

    sources = [
        {
            "source": ligne[0],
            "langue": ligne[1],
            "url": ligne[2],
            "contenu": ligne[3],
            "page_titre": ligne[4],
            "page_type": ligne[5]
        }
        for ligne in lignes
    ]

    filtres_sources = filtres_sources or {}

    sources_filtrees = []

    for source in sources:
        nom_source = source.get("source")
        langue = source.get("langue")
        page_titre = source.get("page_titre")

        if nom_source == "Wiktionary":
            langues = filtres_sources.get("wiktionary", {}).get("langues", [])

            if langues and langue not in langues:
                continue

        if nom_source == "Académie française":
            editions = filtres_sources.get("academie_fr", {}).get("editions", [])

            if editions and page_titre not in editions:
                continue

        sources_filtrees.append(source)

    return sources_filtrees

def nettoyer_contenu_source(contenu):
    if not contenu:
        return ""

    soup = BeautifulSoup(contenu, "html.parser")

    for balise in soup(["script", "style", "nav", "audio"]):
        balise.decompose()

    texte = soup.get_text("\n")

    lignes = [
        ligne.strip()
        for ligne in texte.splitlines()
        if ligne.strip()
    ]

    return "\n".join(lignes)

def construire_prompt_ia(
    mot,
    style,
    longueur,
    requete,
    sources,
    categories,
    sources_trouvees,
    max_sources=None,
    max_caracteres_par_source=2000
):
    mot = mot.lower().strip()

    if isinstance(categories, str):
        categories_liste = [
            categorie.strip()
            for categorie in categories.split(",")
            if categorie.strip()
        ]
    elif categories:
        categories_liste = categories
    else:
        categories_liste = []

    if categories_liste:
        categories_texte = "\n".join(
            [f"- {categorie}" for categorie in categories_liste]
        )
    else:
        categories_texte = "- Toutes les catégories pertinentes selon les sources"
    

    blocs_sources = []

    sources_a_utiliser = sources_trouvees

    if max_sources is not None:
        sources_a_utiliser = sources_trouvees[:max_sources]

    for source in sources_a_utiliser:
        contenu = nettoyer_contenu_source(source.get("contenu") or "")

        if (
            max_caracteres_par_source is not None
            and len(contenu) > max_caracteres_par_source
        ):
            contenu = (
                contenu[:max_caracteres_par_source]
                + "\n[contenu coupé : la suite existe dans la base mais n'est pas incluse dans ce prompt de test]"
            )

        nom_source = source.get("source") or "Source inconnue"

        if source.get("page_titre"):
            nom_source = f"{nom_source} ({source.get('page_titre')})"

        bloc = f"""
    SOURCE : {nom_source}
    LANGUE : {source.get("langue")}
    URL : {source.get("url")}

    CONTENU BRUT :
    {contenu}
    """
        blocs_sources.append(bloc)

    sources_texte = "\n\n====================\n\n".join(blocs_sources)

    prompt = f"""
Ta mission est de produire une fiche intelligente sur le mot : "{mot}".

Tu ne dois pas faire une simple définition de dictionnaire.
Tu dois croiser les sources, repérer les convergences, les différences, les absences et les éventuelles contradictions.

RÈGLES ABSOLUES :
- Utilise uniquement les sources brutes fournies.
- N’ajoute pas d’information extérieure.
- Si une information n’est pas présente, ne l’invente pas et signale son absence si elle était demandée.
- Ne présente pas les informations source par source: ne fais pas 36 fois la même catégorie en présentant une source différente à chaque fois, fais une fois une catégorie en présentant les informations des différentes sources dedans.
- Organise la réponse par catégories.
- Réponds en français, ainsi la seule exception quant aux informations extérieures est ta capacité à traduire.
- Retourne uniquement un JSON valide.

INTERDICTIONS ABSOLUES :
- Ne cite jamais une source qui n’apparaît pas dans les SOURCES BRUTES.
- Dans "sources_utilisees", utilise uniquement les noms exacts indiqués après "SOURCE :".
- Ne recopie jamais les exemples du format attendu comme contenu final.
- Si tu ne sais pas remplir une section, écris une explication honnête plutôt qu’un texte générique.

L'utilisateur pourra choisir un style, une longueur, des catégories ainsi que les sources.
Il pourra aussi te faire un texte détaillant ce qu'il veut.
La demande particulière de l’utilisateur est prioritaire sur les choix de style, de longueur et de catégories.
Elle peut influencer les sections et leur contenu, mais la réponse doit toujours rester un JSON valide.
En revanche, tu ne dois jamais dévier de ta tâche : analyser et interpréter les sources brutes fournies.
Les sources brutes données sont des copies du html ou du wikicode de dictionnaires, encyclopédies et autres sites, il est donc possible qu'il y ait des informations n'ayant aucun rapport avec ta tâche.
Si les sources brutes sont vides, c'est qu'il n'y eut aucune information trouvée.

AVERTISSEMENT VERSION TEST :
Certaines sources peuvent être volontairement coupées dans ce prompt afin d’éviter un texte trop long.
Lorsqu’une source contient la mention "[contenu coupé]", considère que tu n’as pas accès à la suite.
Ne déduis rien à partir de la partie manquante.
Si une information demandée pourrait se trouver dans la partie coupée, indique qu’elle n’est pas visible dans l’extrait fourni.

Pour la catégorie "voyage géographique", distingue clairement :
1. la diffusion historique du mot lui-même ;
2. les équivalents dans d'autres langues ;
3. les homographes ou faux amis sans lien étymologique ;
4. les usages culturels ou idiomatiques.
Ne présente pas les traductions comme si elles étaient toutes issues du mot français.
Dans "sources_utilisees", ne liste pas toutes les variantes linguistiques de Wiktionary une par une.
Regroupe-les sous une forme courte, par exemple :
"Wiktionary multilingue", "Wiktionary français", "Wiktionary anglais".

RÈGLES DE STRUCTURE :
- Distingue les différents sens du mot dans le champ "sens".
- Pour chaque sens, indique s’il est concret, figuré, technique, historique, étymologique, homographe, emprunt, ou autre.
- Ne mélange pas les traductions, les homographes étrangers et l’histoire du mot français.
- Pour la catégorie "voyage_geographique", distingue clairement :
  1. la diffusion historique du mot lui-même ;
  2. les équivalents dans d'autres langues ;
  3. les homographes ou faux amis sans lien étymologique évident ;
  4. les usages culturels ou idiomatiques.
- Ajoute un niveau de fiabilité global : forte, moyenne ou faible.
- Justifie ce niveau de fiabilité à partir des sources fournies.

RÈGLES DE STYLE DU JSON :
- N’utilise pas de Markdown dans les valeurs JSON.
- N’utilise pas d’astérisques pour faire du gras.
- N’utilise pas de listes Markdown avec "*", "-", ou "1." dans les champs "contenu".
- Écris les contenus en phrases claires, lisibles directement en HTML.
- Si tu dois faire une liste, écris-la en phrases séparées, ou crée plusieurs sections.

STYLE DEMANDÉ :
=== BEGIN ===
{style}
=== END ===

LONGUEUR DEMANDÉE :
=== BEGIN ===
{longueur}
=== END ===

CATÉGORIES DEMANDÉES :
=== BEGIN ===
{categories_texte}
=== END ===

DEMANDE PARTICULIÈRE DE L’UTILISATEUR :
=== BEGIN ===
{requete}
=== END ===

FORMAT ATTENDU :
{{
  "mot": "{mot}",
  "resume_general": "Résumé global du mot.",
  "sens": [
    {{
      "titre": "Nom court du sens",
      "type": "concret | figuré | technique | historique | étymologique | homographe | emprunt | autre",
      "description": "Explication claire de ce sens.",
      "exemples": [
        "Exemple ou expression si disponible dans les sources."
      ],
      "sources_utilisees": ["nom des sources utiles"]
    }}
  ],
  "sections": [
    {{
      "titre": "Nom de la section",
      "contenu": "Texte de la section.",
      "sources_utilisees": ["nom des sources utiles"]
    }}
  ],
  "fiabilite": {{
    "niveau": "forte | moyenne | faible",
    "justification": "Justification du niveau de confiance à partir des sources."
  }},
  "contradictions_ou_incertain": [
    "Points incertains ou contradictoires"
  ],
  "informations_absentes": [
    "Informations demandées mais non trouvées dans les sources"
  ]
}}

SOURCES BRUTES :
=== BEGIN ===
{sources_texte}
=== END ===
"""

    return prompt.strip()

def preparer_sources_pour_generation(
    mot,
    sources_choisies,
    reutiliser_sources=True,
    filtres_sources=None
):
    mot = mot.lower().strip()
    filtres_sources = filtres_sources or {}

    if sources_choisies is None:
        sources_choisies = list(SOURCES_PAR_CLE.keys())

    elif isinstance(sources_choisies, str):
        sources_choisies = [
            source.strip()
            for source in sources_choisies.split(",")
            if source.strip()
        ]

    for cle in sources_choisies:
        source_module = SOURCES_PAR_CLE.get(cle)

        if not source_module:
            continue

        # Cas spécial : Wiktionary avec langues sélectionnées
        if cle == "wiktionary":
            langues_demandees = filtres_sources.get("wiktionary", {}).get("langues", [])

            if langues_demandees:
                langues_deja = langues_wiktionary_presentes(mot)
                langues_manquantes = [
                    langue for langue in langues_demandees
                    if langue not in langues_deja
                ]

                if reutiliser_sources and not langues_manquantes:
                    print(f"{source_module.NOM}: langues demandées déjà présentes ✅")
                    continue

                if not reutiliser_sources:
                    supprimer_wiktionary_langues(mot, langues_demandees)
                    langues_a_telecharger = langues_demandees
                else:
                    langues_a_telecharger = langues_manquantes

                print(f"{source_module.NOM}: téléchargement langues {langues_a_telecharger}...")
                telecharger_source_sans_casser(
                    source_module,
                    mot,
                    langues_autorisees=langues_a_telecharger
                )
                continue

            # Si aucune langue précise n'est envoyée, comportement classique
            if reutiliser_sources and source_existe_deja(mot, source_module):
                print(f"{source_module.NOM}: réutilisée ✅")
                continue

            if not reutiliser_sources:
                supprimer_source_brute(mot, source_module)

            print(f"{source_module.NOM}: téléchargement...")
            telecharger_source_sans_casser(source_module, mot)
            continue

        # Cas classique : autres sources
        if reutiliser_sources and source_existe_deja(mot, source_module):
            print(f"{source_module.NOM}: réutilisée ✅")
            continue

        if not reutiliser_sources:
            supprimer_source_brute(mot, source_module)

        print(f"{source_module.NOM}: téléchargement...")
        telecharger_source_sans_casser(source_module, mot)

    conn.commit()

def creation_definition(mot):
    supprimer_mot(mot)

    for source in SOURCES:
        source.telecharger(mot)

    resume = "Sources brutes téléchargées. Résumé IA non généré pour l’instant."
    source = ", ".join([s.NOM for s in SOURCES])

    cur.execute(
        "INSERT INTO definitions VALUES (?, ?, ?, ?)",
        (mot, resume, source, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )

    conn.commit()


def verification_existence_definition(mot):
    cur.execute("SELECT mot FROM definitions WHERE mot = ?", (mot,))
    resultat = cur.fetchone()

    if resultat:
        # déjà présent dans la base
        return

    creation_definition(mot)


def afficher_mot(mot):
    cur.execute("SELECT resume, sources, date_generation FROM definitions WHERE mot = ?", (mot,))
    resultat = cur.fetchone()

    if not resultat:
        verification_existence_definition(mot)
        return afficher_mot(mot)

    resume, sources, date = resultat

    return {
        "mot": mot,
        "resume": resume,
        "sources": sources,
        "date": date
    }

def afficher_liste():
    cur.execute("SELECT mot FROM definitions ORDER BY mot")
    mots = [ligne[0] for ligne in cur.fetchall()]
    return mots

def supprimer_mot(mot_suppr):
    # Suppression des potentielles anciennes définitions et sources...
    cur.execute("DELETE FROM definitions WHERE mot = ?", (mot_suppr,))
    cur.execute("DELETE FROM sources_brutes WHERE mot = ?", (mot_suppr,))
    conn.commit()

def voir_sources(mot):
    mot = mot.lower().strip()

    cur.execute("""
    SELECT id, source, langue, LENGTH(contenu_brut), url, page_titre, page_type
    FROM sources_brutes
    WHERE mot = ? AND existe = 1
    ORDER BY source COLLATE NOCASE, page_titre COLLATE NOCASE, langue COLLATE NOCASE
    """, (mot,))

    resultats = cur.fetchall()

    sources = []

    for id_source, source, langue, taille, url, page_titre, page_type in resultats:
        sources.append({
            "id": id_source,
            "source": source,
            "langue": langue,
            "taille": taille,
            "url": url,
            "page_titre": page_titre,
            "page_type": page_type
        })

    return sources

def lire_source_brute(id_source):
    cur.execute("""
    SELECT id, source, langue, url, contenu_brut, page_titre, page_type, LENGTH(contenu_brut)
    FROM sources_brutes
    WHERE id = ?
    """, (id_source,))

    ligne = cur.fetchone()

    if not ligne:
        return {
            "erreur": True,
            "message": "Source brute introuvable."
        }

    return {
        "erreur": False,
        "id": ligne[0],
        "source": ligne[1],
        "langue": ligne[2],
        "url": ligne[3],
        "contenu_brut": ligne[4],
        "page_titre": ligne[5],
        "page_type": ligne[6],
        "taille": ligne[7]
    }

def enregistrer_generation(
    mot,
    style,
    longueur,
    requete,
    sources,
    categories,
    contenu,
    filtres_sources="",
    user_id=None,
    nom_utilisateur=None
):
    cur.execute("""
    INSERT INTO generations (
        mot,
        style,
        longueur,
        requete_utilisateur,
        sources_choisies,
        categories_choisies,
        contenu,
        date_generation,
        filtres_sources,
        user_id,
        nom_utilisateur
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        mot,
        style,
        longueur,
        requete,
        sources,
        categories,
        contenu,
        datetime.now().strftime("%d/%m/%Y %H:%M"),
        filtres_sources,
        user_id,
        nom_utilisateur
    ))

    conn.commit()
    return cur.lastrowid

def lire_generation(id_generation):
    cur.execute("""
    SELECT
        generations.id,
        generations.mot,
        generations.style,
        generations.longueur,
        generations.requete_utilisateur,
        generations.sources_choisies,
        generations.categories_choisies,
        generations.contenu,
        generations.date_generation,
        generations.filtres_sources,
        generations.user_id,
        utilisateurs.nom_utilisateur,
        utilisateurs.identifiant_public,
        generations.nom_utilisateur
    FROM generations
    LEFT JOIN utilisateurs
        ON utilisateurs.id = generations.user_id
    WHERE generations.id = ?
    """, (id_generation,))

    ligne = cur.fetchone()

    if not ligne:
        return {
            "erreur": True,
            "message": "Génération introuvable."
        }
    
    return {
        "id": ligne[0],
        "mot": ligne[1],
        "style": ligne[2],
        "longueur": ligne[3],
        "requete_utilisateur": ligne[4],
        "sources_choisies": ligne[5],
        "categories_choisies": ligne[6],
        "contenu": ligne[7],
        "date_generation": ligne[8],
        "filtres_sources": ligne[9],
        "user_id": ligne[10],
        "nom_utilisateur": ligne[11] or ligne[13],
        "identifiant_public": ligne[12],
        "nom_utilisateur_creation": ligne[13]
    }

def supprimer_generation(id_generation):
    cur.execute(
        "DELETE FROM generations WHERE id = ?",
        (id_generation,)
    )

    conn.commit()

    return cur.rowcount > 0

def sources_existent(mot):
    cur.execute("""
    SELECT COUNT(*)
    FROM sources_brutes
    WHERE mot = ? AND existe = 1
    """, (mot,))

    nombre = cur.fetchone()[0]
    return nombre > 0

def assurer_sources(mot):
    mot = mot.lower().strip()

    if not sources_existent(mot):
        creation_definition(mot)

    return True

def programme(mot):
    mot = mot.lower().strip()
    return afficher_mot(mot)