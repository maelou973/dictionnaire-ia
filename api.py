from fastapi import FastAPI
from fastapi.responses import FileResponse
from database import conn, cur
from ia import demander_a_ia
import json
from fastapi.staticfiles import StaticFiles
from fastapi import Request, Response
from pydantic import BaseModel
from typing import Optional
from sources.informations_sources import INFORMATIONS_SOURCES

# compte google: larmazadouemael@gmail.com
# clef API (a ne pas mettre en clair dans v_final): 

from comptes import (
    creer_utilisateur,
    verifier_identifiants,
    creer_session,
    utilisateur_depuis_token,
    supprimer_session,
    modifier_nom_utilisateur,
    modifier_email,
    modifier_mot_de_passe
)
from main import (
    programme,
    afficher_liste,
    voir_sources,
    enregistrer_generation,
    preparer_sources_pour_generation,
    recuperer_sources_pour_generation,
    construire_prompt_ia,
    supprimer_generation,
    lire_source_brute,
    options_sources,
    lire_generation
)

app = FastAPI()
app.mount("/static", StaticFiles(directory="affichage web"), name="static")

class DonneesCompte(BaseModel):
    nom_utilisateur: str
    mot_de_passe: str
    email: str = ""

class DonneesPseudo(BaseModel):
    nouveau_nom_utilisateur: str
    mot_de_passe: str


class DonneesEmail(BaseModel):
    nouvel_email: str
    mot_de_passe: str


class DonneesMotDePasse(BaseModel):
    ancien_mot_de_passe: str
    nouveau_mot_de_passe: str

class DonneesGeneration(BaseModel):
    mot: str
    style: str = "académique"
    longueur: str = "moyenne"
    requete: str = ""
    sources: Optional[list[str]] = None
    categories: Optional[list[str]] = None
    reutiliser_sources: bool = True
    mode_test: bool = False
    filtres_sources: dict = {}

@app.get("/")
def accueil():
    return FileResponse("affichage web/index.html")

@app.get("/compte")
def page_compte():
    return FileResponse("affichage web/index.html")

@app.get("/options_sources")
def route_options_sources():

    resultat = options_sources()

    resultat["sources"] = [
        {
            "id": identifiant,
            "nom": informations["nom"],
            "active_par_defaut": informations["active_par_defaut"]
        }
        for identifiant, informations in INFORMATIONS_SOURCES.items()
    ]

    return resultat

@app.get("/chercher")
def chercher(mot: str):
    return programme(mot)

@app.get("/liste")
def liste():
    return afficher_liste()

@app.post("/inscription")
def route_inscription(donnees: DonneesCompte, response: Response):
    resultat = creer_utilisateur(
        donnees.nom_utilisateur,
        donnees.mot_de_passe,
        donnees.email
    )

    if resultat["erreur"]:
        return resultat

    utilisateur = resultat["utilisateur"]
    token = creer_session(utilisateur["id"])

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30
    )

    return {
        "erreur": False,
        "message": "Compte créé et connexion effectuée.",
        "utilisateur": utilisateur
    }

@app.post("/compte/pseudo")
def route_modifier_pseudo(donnees: DonneesPseudo, request: Request):
    token = request.cookies.get("session")
    utilisateur = utilisateur_depuis_token(token)

    if not utilisateur:
        return {
            "erreur": True,
            "message": "Tu dois être connecté."
        }

    return modifier_nom_utilisateur(
        utilisateur["id"],
        donnees.nouveau_nom_utilisateur,
        donnees.mot_de_passe
    )


@app.post("/compte/email")
def route_modifier_email(donnees: DonneesEmail, request: Request):
    token = request.cookies.get("session")
    utilisateur = utilisateur_depuis_token(token)

    if not utilisateur:
        return {
            "erreur": True,
            "message": "Tu dois être connecté."
        }

    return modifier_email(
        utilisateur["id"],
        donnees.nouvel_email,
        donnees.mot_de_passe
    )


@app.post("/compte/mot_de_passe")
def route_modifier_mot_de_passe(donnees: DonneesMotDePasse, request: Request):
    token = request.cookies.get("session")
    utilisateur = utilisateur_depuis_token(token)

    if not utilisateur:
        return {
            "erreur": True,
            "message": "Tu dois être connecté."
        }

    return modifier_mot_de_passe(
        utilisateur["id"],
        donnees.ancien_mot_de_passe,
        donnees.nouveau_mot_de_passe
    )

@app.get("/mes_generations")
def route_mes_generations(request: Request):
    token = request.cookies.get("session")
    utilisateur = utilisateur_depuis_token(token)

    if not utilisateur:
        return {
            "erreur": True,
            "message": "Tu dois être connecté.",
            "generations": []
        }

    cur.execute("""
    SELECT
        id,
        mot,
        style,
        longueur,
        date_generation,
        sources_choisies,
        categories_choisies
    FROM generations
    WHERE user_id = ?
    ORDER BY id DESC
    """, (utilisateur["id"],))

    lignes = cur.fetchall()

    return {
        "erreur": False,
        "generations": [
            {
                "id": ligne[0],
                "mot": ligne[1],
                "style": ligne[2],
                "longueur": ligne[3],
                "date_generation": ligne[4],
                "sources_choisies": ligne[5],
                "categories_choisies": ligne[6]
            }
            for ligne in lignes
        ]
    }

@app.post("/connexion")
def route_connexion(donnees: DonneesCompte, response: Response):
    utilisateur = verifier_identifiants(
        donnees.nom_utilisateur,
        donnees.mot_de_passe
    )

    if not utilisateur:
        return {
            "erreur": True,
            "message": "Nom d’utilisateur ou mot de passe incorrect."
        }

    token = creer_session(utilisateur["id"])

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30
    )

    return {
        "erreur": False,
        "message": "Connexion réussie.",
        "utilisateur": utilisateur
    }


@app.post("/deconnexion")
def route_deconnexion(request: Request, response: Response):
    token = request.cookies.get("session")
    supprimer_session(token)

    response.delete_cookie("session")

    return {
        "erreur": False,
        "message": "Déconnexion effectuée."
    }


@app.get("/moi")
def route_moi(request: Request):
    token = request.cookies.get("session")
    utilisateur = utilisateur_depuis_token(token)

    if not utilisateur:
        return {
            "connecte": False,
            "utilisateur": None
        }

    return {
        "connecte": True,
        "utilisateur": utilisateur
    }

@app.get("/source_brute")
def route_source_brute(id: int):
    return lire_source_brute(id)

@app.get("/utilisateur/{nom_utilisateur}")
def page_utilisateur(nom_utilisateur: str):
    return FileResponse("affichage web/index.html")

@app.get("/api/utilisateur/{id_profil}")
def route_profil_utilisateur(id_profil: str):
    cur.execute("""
    SELECT
        id,
        identifiant_public,
        nom_utilisateur,
        date_creation,
        role
    FROM utilisateurs
    WHERE identifiant_public = ?
    """, (id_profil,))

    utilisateur = cur.fetchone()

    if not utilisateur:
        return {
            "erreur": True,
            "message": "Utilisateur introuvable."
        }

    user_id = utilisateur[0]

    cur.execute("""
    SELECT
        id,
        mot,
        style,
        longueur,
        date_generation,
        sources_choisies,
        categories_choisies
    FROM generations
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT 50
    """, (user_id,))

    lignes = cur.fetchall()

    return {
        "erreur": False,
        "utilisateur": {
            "id_profil": utilisateur[1],
            "nom_utilisateur": utilisateur[2],
            "date_creation": utilisateur[3],
            "role": utilisateur[4]
        },
        "generations": [
            {
                "id": ligne[0],
                "mot": ligne[1],
                "style": ligne[2],
                "longueur": ligne[3],
                "date_generation": ligne[4],
                "sources_choisies": ligne[5],
                "categories_choisies": ligne[6]
            }
            for ligne in lignes
        ]
    }

@app.delete("/generation")
def route_supprimer_generation(id: int, request: Request):
    token = request.cookies.get("session")
    utilisateur = utilisateur_depuis_token(token)

    if not utilisateur:
        return {
            "erreur": True,
            "message": "Tu dois être connecté pour supprimer une génération."
        }

    generation = lire_generation(id)

    if not generation:
        return {
            "erreur": True,
            "message": "Génération introuvable."
        }

    createur_id = generation.get("user_id")

    if createur_id is not None:
        if utilisateur["id"] != createur_id and utilisateur.get("role") != "admin":
            return {
                "erreur": True,
                "message": "Tu ne peux pas supprimer une génération créée par un autre utilisateur."
            }

    ok = supprimer_generation(id)

    return {
        "erreur": not ok,
        "message": "Génération supprimée." if ok else "Suppression impossible."
    }

@app.get("/sources")
def route_sources(mot: str):
    return voir_sources(mot)

@app.get("/generations")
def generations(mot: str):
    cur.execute("""
    SELECT id, style, longueur, date_generation
    FROM generations
    WHERE mot = ?
    ORDER BY id DESC
    """, (mot,))

    return [
        {
            "id": ligne[0],
            "style": ligne[1],
            "longueur": ligne[2],
            "date": ligne[3]
        }
        for ligne in cur.fetchall()
    ]

@app.get("/generation")
def generation(id: int):
    return lire_generation(id)

@app.post("/generer_personnalise")
def generer_personnalise(donnees: DonneesGeneration, request: Request):
    token = request.cookies.get("session")
    utilisateur = utilisateur_depuis_token(token)

    if not utilisateur:
        return {
            "erreur": True,
            "message": "Tu dois être connecté pour créer une fiche."
        }

    mot = donnees.mot.strip().lower()
    sources_choisies = donnees.sources
    categories_choisies = donnees.categories or []
    filtres_sources_dict = donnees.filtres_sources or {}

    if not mot:
        return {
            "erreur": True,
            "message": "Entre un mot à explorer."
        }

    if sources_choisies is not None and len(sources_choisies) == 0:
        return {
            "erreur": True,
            "message": "Choisis au moins une source pour générer une fiche."
        }

    preparer_sources_pour_generation(
        mot,
        sources_choisies,
        reutiliser_sources=donnees.reutiliser_sources,
        filtres_sources=filtres_sources_dict
    )

    sources_trouvees = recuperer_sources_pour_generation(
        mot,
        sources_choisies,
        filtres_sources=filtres_sources_dict
    )

    prompt_ia = construire_prompt_ia(
        mot=mot,
        style=donnees.style,
        longueur=donnees.longueur,
        requete=donnees.requete,
        sources=sources_choisies,
        categories=categories_choisies,
        sources_trouvees=sources_trouvees,
        max_sources=None,
        max_caracteres_par_source=None
    )

    if donnees.mode_test:
        return {
            "erreur": False,
            "mode_test": True,
            "message": "Mode test : prompt généré sans appel à l’IA.",
            "prompt": prompt_ia,
            "contenu": prompt_ia,
            "id": None
        }

    if not sources_trouvees:
        return {
            "erreur": True,
            "message": "Aucune source exploitable trouvée pour ce mot avec ces options.",
            "prompt": prompt_ia
        }

    try:
        contenu = demander_a_ia(prompt_ia)
    except Exception as e:
        return {
            "erreur": True,
            "message": f"Erreur lors de l’appel à l’IA : {type(e).__name__}: {e}",
            "prompt": prompt_ia
        }

    sources_csv = ",".join(sources_choisies or [])
    categories_csv = ",".join(categories_choisies or [])
    filtres_sources_json = json.dumps(filtres_sources_dict, ensure_ascii=False)

    id_generation = enregistrer_generation(
        mot,
        donnees.style,
        donnees.longueur,
        donnees.requete,
        sources_csv,
        categories_csv,
        contenu,
        filtres_sources=filtres_sources_json,
        user_id=utilisateur["id"],
        nom_utilisateur=utilisateur["nom_utilisateur"]
    )

    return {
        "erreur": False,
        "message": "Génération IA enregistrée.",
        "contenu": contenu,
        "id": id_generation
    }

@app.get("/dictionnaire/{mot}")
def page_mot(mot: str):
    return FileResponse("affichage web/index.html")


@app.get("/dictionnaire/{mot}/{id_generation}")
def page_generation(mot: str, id_generation: int):
    return FileResponse("affichage web/index.html")


@app.get("/utilisateur/{id_profil}")
def page_utilisateur(id_profil: str):
    return FileResponse("affichage web/index.html")