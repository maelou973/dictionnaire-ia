import os
import json
import time
from google import genai

MODELE_IA = "gemini-2.5-flash"

cle_api = os.environ.get("GEMINI_API_KEY")
#compte google: larmazadouemael@gmail.com
#clef API (a ne pas mettre en clair dans v_final): AQ.Ab8RN6JxWYE6vn8eDsvKr4DP11ijTM-hqhhVlsqAgAewBm97oA

if not cle_api:
    raise RuntimeError(
        "La variable d'environnement GEMINI_API_KEY est absente. "
        "Définis-la dans PowerShell avant de lancer uvicorn."
    )

client = genai.Client(api_key=cle_api)


def nettoyer_reponse_json(texte):
    texte = texte.strip()

    if texte.startswith("```json"):
        texte = texte.removeprefix("```json").strip()

    if texte.startswith("```"):
        texte = texte.removeprefix("```").strip()

    if texte.endswith("```"):
        texte = texte.removesuffix("```").strip()

    return texte


def demander_a_ia(prompt):
    derniere_erreur = None

    for tentative in range(4):
        try:
            reponse = client.models.generate_content(
                model=MODELE_IA,
                contents=prompt
            )

            texte = nettoyer_reponse_json(reponse.text)
            json.loads(texte)

            return texte

        except Exception as e:
            derniere_erreur = e
            message = str(e)

            if ("503" in message or "UNAVAILABLE" in message) and tentative < 3:
                time.sleep(2 + tentative * 4)
                continue

            raise derniere_erreur