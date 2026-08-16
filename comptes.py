from datetime import datetime
import base64
import hashlib
import hmac
import re
import secrets
import sqlite3

from database import cur, conn


NB_ITERATIONS = 210_000


def normaliser_nom_utilisateur(nom):
    return nom.strip()


def normaliser_email(email):
    email = (email or "").strip().lower()

    if not email:
        return None

    return email


def email_valide(email):
    if not email:
        return False

    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


def nouvel_identifiant_public():
    return "u_" + secrets.token_urlsafe(12).replace("-", "").replace("_", "")


def generer_identifiant_public_unique():
    while True:
        identifiant = nouvel_identifiant_public()

        cur.execute("""
        SELECT id
        FROM utilisateurs
        WHERE identifiant_public = ?
        """, (identifiant,))

        if not cur.fetchone():
            return identifiant


def hacher_mot_de_passe(mot_de_passe):
    sel = secrets.token_bytes(16)

    empreinte = hashlib.pbkdf2_hmac(
        "sha256",
        mot_de_passe.encode("utf-8"),
        sel,
        NB_ITERATIONS
    )

    sel_b64 = base64.b64encode(sel).decode("ascii")
    empreinte_b64 = base64.b64encode(empreinte).decode("ascii")

    return f"pbkdf2_sha256${NB_ITERATIONS}${sel_b64}${empreinte_b64}"


def verifier_mot_de_passe(mot_de_passe, mot_de_passe_hash):
    try:
        algo, iterations, sel_b64, empreinte_b64 = mot_de_passe_hash.split("$")
    except ValueError:
        return False

    if algo != "pbkdf2_sha256":
        return False

    sel = base64.b64decode(sel_b64.encode("ascii"))
    empreinte_attendue = base64.b64decode(empreinte_b64.encode("ascii"))

    empreinte_test = hashlib.pbkdf2_hmac(
        "sha256",
        mot_de_passe.encode("utf-8"),
        sel,
        int(iterations)
    )

    return hmac.compare_digest(empreinte_test, empreinte_attendue)


def hacher_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def creer_utilisateur(nom_utilisateur, mot_de_passe, email):
    nom_utilisateur = normaliser_nom_utilisateur(nom_utilisateur)
    email = normaliser_email(email)

    if len(nom_utilisateur) < 3:
        return {
            "erreur": True,
            "message": "Le nom d’utilisateur doit contenir au moins 3 caractères."
        }

    if not email_valide(email):
        return {
            "erreur": True,
            "message": "Adresse e-mail invalide."
        }

    if len(mot_de_passe) < 6:
        return {
            "erreur": True,
            "message": "Le mot de passe doit contenir au moins 6 caractères."
        }

    cur.execute("""
    SELECT id
    FROM utilisateurs
    WHERE nom_utilisateur = ?
    """, (nom_utilisateur,))

    if cur.fetchone():
        return {
            "erreur": True,
            "message": "Ce nom d’utilisateur existe déjà."
        }

    cur.execute("""
    SELECT id
    FROM utilisateurs
    WHERE email = ?
    """, (email,))

    if cur.fetchone():
        return {
            "erreur": True,
            "message": "Cette adresse e-mail est déjà utilisée."
        }

    mot_de_passe_hash = hacher_mot_de_passe(mot_de_passe)
    identifiant_public = generer_identifiant_public_unique()

    try:
        cur.execute("""
        INSERT INTO utilisateurs (
            identifiant_public,
            email,
            nom_utilisateur,
            mot_de_passe_hash,
            date_creation,
            role
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            identifiant_public,
            email,
            nom_utilisateur,
            mot_de_passe_hash,
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            "utilisateur"
        ))

        conn.commit()

    except sqlite3.IntegrityError:
        return {
            "erreur": True,
            "message": "Compte impossible à créer : pseudo ou e-mail déjà utilisé."
        }

    return {
        "erreur": False,
        "message": "Compte créé.",
        "utilisateur": {
            "id": cur.lastrowid,
            "identifiant_public": identifiant_public,
            "nom_utilisateur": nom_utilisateur,
            "email": email,
            "role": "utilisateur"
        }
    }


def verifier_identifiants(identifiant, mot_de_passe):
    identifiant = normaliser_nom_utilisateur(identifiant)
    email_possible = normaliser_email(identifiant)

    cur.execute("""
    SELECT
        id,
        identifiant_public,
        nom_utilisateur,
        email,
        mot_de_passe_hash,
        role
    FROM utilisateurs
    WHERE nom_utilisateur = ?
       OR email = ?
    """, (
        identifiant,
        email_possible
    ))

    ligne = cur.fetchone()

    if not ligne:
        return None

    if not verifier_mot_de_passe(mot_de_passe, ligne[4]):
        return None

    return {
        "id": ligne[0],
        "identifiant_public": ligne[1],
        "nom_utilisateur": ligne[2],
        "email": ligne[3],
        "role": ligne[5]
    }


def creer_session(user_id):
    token = secrets.token_urlsafe(32)
    token_hash = hacher_token(token)

    cur.execute("""
    INSERT INTO sessions (
        user_id,
        token_hash,
        date_creation
    )
    VALUES (?, ?, ?)
    """, (
        user_id,
        token_hash,
        datetime.now().strftime("%d/%m/%Y %H:%M")
    ))

    conn.commit()

    return token


def utilisateur_depuis_token(token):
    if not token:
        return None

    token_hash = hacher_token(token)

    cur.execute("""
    SELECT
        utilisateurs.id,
        utilisateurs.identifiant_public,
        utilisateurs.nom_utilisateur,
        utilisateurs.email,
        utilisateurs.role
    FROM sessions
    JOIN utilisateurs ON utilisateurs.id = sessions.user_id
    WHERE sessions.token_hash = ?
    """, (token_hash,))

    ligne = cur.fetchone()

    if not ligne:
        return None

    return {
        "id": ligne[0],
        "identifiant_public": ligne[1],
        "nom_utilisateur": ligne[2],
        "email": ligne[3],
        "role": ligne[4]
    }


def supprimer_session(token):
    if not token:
        return

    token_hash = hacher_token(token)

    cur.execute("""
    DELETE FROM sessions
    WHERE token_hash = ?
    """, (token_hash,))

    conn.commit()

def utilisateur_depuis_id(user_id):
    cur.execute("""
    SELECT
        id,
        identifiant_public,
        nom_utilisateur,
        email,
        role
    FROM utilisateurs
    WHERE id = ?
    """, (user_id,))

    ligne = cur.fetchone()

    if not ligne:
        return None

    return {
        "id": ligne[0],
        "identifiant_public": ligne[1],
        "nom_utilisateur": ligne[2],
        "email": ligne[3],
        "role": ligne[4]
    }


def verifier_mot_de_passe_utilisateur(user_id, mot_de_passe):
    cur.execute("""
    SELECT mot_de_passe_hash
    FROM utilisateurs
    WHERE id = ?
    """, (user_id,))

    ligne = cur.fetchone()

    if not ligne:
        return False

    return verifier_mot_de_passe(mot_de_passe, ligne[0])


def modifier_nom_utilisateur(user_id, nouveau_nom, mot_de_passe):
    nouveau_nom = normaliser_nom_utilisateur(nouveau_nom)

    if len(nouveau_nom) < 3:
        return {
            "erreur": True,
            "message": "Le pseudo doit contenir au moins 3 caractères."
        }

    if not verifier_mot_de_passe_utilisateur(user_id, mot_de_passe):
        return {
            "erreur": True,
            "message": "Mot de passe incorrect."
        }

    cur.execute("""
    SELECT id
    FROM utilisateurs
    WHERE nom_utilisateur = ?
      AND id != ?
    """, (nouveau_nom, user_id))

    if cur.fetchone():
        return {
            "erreur": True,
            "message": "Ce pseudo est déjà utilisé."
        }

    cur.execute("""
    UPDATE utilisateurs
    SET nom_utilisateur = ?
    WHERE id = ?
    """, (nouveau_nom, user_id))

    conn.commit()

    return {
        "erreur": False,
        "message": "Pseudo modifié.",
        "utilisateur": utilisateur_depuis_id(user_id)
    }


def modifier_email(user_id, nouvel_email, mot_de_passe):
    nouvel_email = normaliser_email(nouvel_email)

    if not email_valide(nouvel_email):
        return {
            "erreur": True,
            "message": "Adresse e-mail invalide."
        }

    if not verifier_mot_de_passe_utilisateur(user_id, mot_de_passe):
        return {
            "erreur": True,
            "message": "Mot de passe incorrect."
        }

    cur.execute("""
    SELECT id
    FROM utilisateurs
    WHERE email = ?
      AND id != ?
    """, (nouvel_email, user_id))

    if cur.fetchone():
        return {
            "erreur": True,
            "message": "Cette adresse e-mail est déjà utilisée."
        }

    cur.execute("""
    UPDATE utilisateurs
    SET email = ?
    WHERE id = ?
    """, (nouvel_email, user_id))

    conn.commit()

    return {
        "erreur": False,
        "message": "E-mail modifié.",
        "utilisateur": utilisateur_depuis_id(user_id)
    }


def modifier_mot_de_passe(user_id, ancien_mot_de_passe, nouveau_mot_de_passe):
    if len(nouveau_mot_de_passe) < 6:
        return {
            "erreur": True,
            "message": "Le nouveau mot de passe doit contenir au moins 6 caractères."
        }

    if not verifier_mot_de_passe_utilisateur(user_id, ancien_mot_de_passe):
        return {
            "erreur": True,
            "message": "Ancien mot de passe incorrect."
        }

    nouveau_hash = hacher_mot_de_passe(nouveau_mot_de_passe)

    cur.execute("""
    UPDATE utilisateurs
    SET mot_de_passe_hash = ?
    WHERE id = ?
    """, (nouveau_hash, user_id))

    conn.commit()

    return {
        "erreur": False,
        "message": "Mot de passe modifié."
    }