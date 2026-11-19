"""
IA_CHAT.PY — Assistant IA Interactif avec OpenRouter
Smart City Neo-Sousse 2030
"""

import sys
import os
import json
import datetime

from openai import OpenAI
from dotenv import load_dotenv

# ───────────────────────────────
# CONFIGURATION DES CHEMINS
# ───────────────────────────────

base = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(base)

# Supporte les deux cas :
# backend/ia_chat.py avec backend/bdd
# backend/ia/ia_chat.py avec backend/bdd
for path in [
    os.path.join(base, "bdd"),
    os.path.join(parent, "bdd"),
]:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

from db_config import get_cursor, test_connection

# ───────────────────────────────
# CONFIGURATION OPENROUTER
# ───────────────────────────────

load_dotenv()
load_dotenv(os.path.join(base, ".env"))
load_dotenv(os.path.join(parent, ".env"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/auto")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY manquante dans le fichier .env")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "http://localhost:5173",
        "X-OpenRouter-Title": "Smart City Neo-Sousse 2030",
    },
)

# ───────────────────────────────
# CONTEXTE BASE DE DONNÉES
# ───────────────────────────────

def collecter_contexte_bd() -> str:
    try:
        with get_cursor() as cur:
            cur.execute("SELECT id, type, zone, statut FROM capteurs ORDER BY id")
            capteurs = [dict(r) for r in cur.fetchall()]

            cur.execute("SELECT id, capteur_id, statut, date FROM interventions ORDER BY id")
            interventions = []
            for r in cur.fetchall():
                d = dict(r)
                d["date"] = str(d.get("date", ""))
                interventions.append(d)

            cur.execute("""
                SELECT capteur_id, type_mesure, valeur, date
                FROM mesures
                ORDER BY date DESC
                LIMIT 10
            """)
            mesures = []
            for r in cur.fetchall():
                d = dict(r)
                d["date"] = str(d.get("date", ""))
                mesures.append(d)

        return f"""
=== SMART CITY DATA — {datetime.date.today()} ===

CAPTEURS:
{json.dumps(capteurs, indent=2, ensure_ascii=False, default=str)}

INTERVENTIONS:
{json.dumps(interventions, indent=2, ensure_ascii=False, default=str)}

MESURES:
{json.dumps(mesures, indent=2, ensure_ascii=False, default=str)}
"""
    except Exception as e:
        return f"[Erreur BD : {e}]"


# ───────────────────────────────
# APPEL OPENROUTER
# ───────────────────────────────

def appeler_openrouter(historique, contexte):
    try:
        messages = [
            {
                "role": "system",
                "content": f"""
Tu es ARIA, l'intelligence artificielle de la Smart City Neo-Sousse 2030.

Tu aides les gestionnaires urbains à :
- analyser les données
- détecter les anomalies
- proposer des actions
- répondre clairement

Réponds toujours en français, de façon professionnelle.

Données actuelles :
{contexte}
"""
            }
        ]

        messages.extend(historique)

        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=800,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Erreur OpenRouter: {e}"


# ───────────────────────────────
# CLASSE ASSISTANT
# ───────────────────────────────

class AssistantIA:
    def __init__(self):
        self.historique = []
        self.contexte = collecter_contexte_bd()

    def rafraichir(self):
        print("Mise à jour des données...")
        self.contexte = collecter_contexte_bd()
        print("Données mises à jour\n")

    def poser_question(self, question):
        self.historique.append({"role": "user", "content": question})

        reponse = appeler_openrouter(self.historique, self.contexte)

        self.historique.append({"role": "assistant", "content": reponse})

        if len(self.historique) > 20:
            self.historique = self.historique[-20:]

        return reponse


# ───────────────────────────────
# MODE INTERACTIF
# ───────────────────────────────

def mode_interactif():
    if not test_connection():
        print("PostgreSQL non disponible")
        return

    assistant = AssistantIA()

    print("\nARIA — Smart City Assistant avec OpenRouter")
    print("Tape 'refresh' pour actualiser les données")
    print("Tape 'quit' pour quitter\n")

    while True:
        question = input("Vous > ").strip()

        if question.lower() == "quit":
            break

        if question.lower() == "refresh":
            assistant.rafraichir()
            continue

        if not question:
            continue

        reponse = assistant.poser_question(question)
        print("\nARIA >", reponse, "\n")


# ───────────────────────────────
# ENTRY POINT
# ───────────────────────────────

if __name__ == "__main__":
    mode_interactif()