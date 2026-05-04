"""
IA_MODULE.PY — Module d'Intelligence Artificielle Générative
Smart City Neo-Sousse 2030 — Propulsé par OpenRouter

Ce module fournit :
  - Collecte de données temps réel depuis PostgreSQL
  - Génération de rapports journaliers professionnels
  - Suggestions d'actions prioritaires pour les gestionnaires
  - Validation intelligente des transitions d'automates
  - Chat interactif avec ARIA
"""

import sys
import os
import json
import re
import datetime

from openai import OpenAI
from dotenv import load_dotenv

# ───────────────────────────────
# CONFIGURATION DES CHEMINS
# ───────────────────────────────

base = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(base)

for path in [
    os.path.join(base, "bdd"),
    os.path.join(parent, "bdd"),
]:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

from db_config import get_cursor

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

# ══════════════════════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════════════════════

def normaliser_statut(value):
    if value is None:
        return ""

    value = str(value).upper()
    replacements = {
        "É": "E",
        "È": "E",
        "Ê": "E",
        "À": "A",
        "Ç": "C",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return value


def appeler_openrouter(historique: list, contexte_bd: str = "", max_tokens: int = 800, temperature: float = 0.7) -> str:
    try:
        messages = [
            {
                "role": "system",
                "content": f"""
Tu es ARIA, l'IA de Neo-Sousse 2030.
Réponds toujours en français.
Analyse les données urbaines et sois professionnel.

{contexte_bd}
"""
            }
        ]

        messages.extend(historique)

        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Erreur OpenRouter: {e}"


def appeler_openrouter_prompt(prompt: str, contexte_bd: str = "", max_tokens: int = 800, temperature: float = 0.7) -> str:
    return appeler_openrouter(
        historique=[{"role": "user", "content": prompt}],
        contexte_bd=contexte_bd,
        max_tokens=max_tokens,
        temperature=temperature,
    )


# ══════════════════════════════════════════════════════════════
# COLLECTE DES DONNÉES DEPUIS POSTGRESQL
# ══════════════════════════════════════════════════════════════

def collecter_donnees_bd() -> dict:
    donnees = {}

    try:
        with get_cursor() as cur:
            cur.execute("""
                SELECT id, type, zone, statut, date_installation
                FROM capteurs
                ORDER BY id
            """)
            donnees["capteurs"] = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT id, capteur_id, technicien1_id, technicien2_id, statut, date
                FROM interventions
                ORDER BY id
            """)
            interventions = []
            for r in cur.fetchall():
                d = dict(r)
                if d.get("date"):
                    d["date"] = str(d["date"])
                interventions.append(d)
            donnees["interventions"] = interventions

            cur.execute("""
                SELECT id, capteur_id, type_mesure, valeur, date
                FROM mesures
                ORDER BY date DESC
                LIMIT 50
            """)
            mesures = []
            for r in cur.fetchall():
                d = dict(r)
                if d.get("date"):
                    d["date"] = str(d["date"])
                if d.get("valeur") is not None:
                    d["valeur"] = float(d["valeur"])
                mesures.append(d)
            donnees["mesures"] = mesures

            cur.execute("""
                SELECT id, nom, score_ecolo, adresse
                FROM citoyens
                ORDER BY id
            """)
            citoyens = []
            for r in cur.fetchall():
                d = dict(r)
                if d.get("score_ecolo") is not None:
                    d["score_ecolo"] = float(d["score_ecolo"])
                citoyens.append(d)
            donnees["citoyens"] = citoyens

            cur.execute("""
                SELECT id, type, trajet_id, statut
                FROM vehicules
                ORDER BY id
            """)
            donnees["vehicules"] = [dict(r) for r in cur.fetchall()]

    except Exception as e:
        print(f"[Erreur collecte BD] {e}")

    return donnees


def statistiques_rapides(donnees: dict) -> dict:
    stats = {}

    capteurs = donnees.get("capteurs", [])
    stats["total_capteurs"] = len(capteurs)
    stats["capteurs_actifs"] = len([c for c in capteurs if normaliser_statut(c.get("statut")) == "ACTIF"])
    stats["capteurs_hs"] = len([c for c in capteurs if normaliser_statut(c.get("statut")) == "HORS_SERVICE"])
    stats["capteurs_signales"] = len([c for c in capteurs if normaliser_statut(c.get("statut")) == "SIGNALE"])
    stats["capteurs_maintenance"] = len([c for c in capteurs if normaliser_statut(c.get("statut")) == "EN_MAINTENANCE"])
    stats["capteurs_hs_details"] = [c for c in capteurs if normaliser_statut(c.get("statut")) == "HORS_SERVICE"]

    interventions = donnees.get("interventions", [])
    stats["total_interventions"] = len(interventions)
    stats["interventions_en_cours"] = len([
        i for i in interventions
        if normaliser_statut(i.get("statut")) not in ("TERMINE",)
    ])
    stats["interventions_terminees"] = len([
        i for i in interventions
        if normaliser_statut(i.get("statut")) == "TERMINE"
    ])

    mesures = donnees.get("mesures", [])
    valeurs = [float(m["valeur"]) for m in mesures if m.get("valeur") is not None]
    stats["moyenne_mesures"] = round(sum(valeurs) / len(valeurs), 2) if valeurs else 0
    stats["max_mesure"] = round(max(valeurs), 2) if valeurs else 0
    stats["min_mesure"] = round(min(valeurs), 2) if valeurs else 0

    vehicules = donnees.get("vehicules", [])
    stats["total_vehicules"] = len(vehicules)
    stats["vehicules_en_route"] = len([v for v in vehicules if normaliser_statut(v.get("statut")) == "EN_ROUTE"])
    stats["vehicules_en_panne"] = len([v for v in vehicules if normaliser_statut(v.get("statut")) == "EN_PANNE"])
    stats["vehicules_panne_details"] = [v for v in vehicules if normaliser_statut(v.get("statut")) == "EN_PANNE"]

    citoyens = donnees.get("citoyens", [])
    scores = [float(c["score_ecolo"]) for c in citoyens if c.get("score_ecolo") is not None]
    stats["score_moyen_citoyens"] = round(sum(scores) / len(scores), 2) if scores else 0
    stats["total_citoyens"] = len(citoyens)

    return stats


# ══════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE — IA GÉNÉRATIVE
# ══════════════════════════════════════════════════════════════

class IAGenerative:
    def __init__(self):
        self.date_aujourd_hui = datetime.date.today().strftime("%d/%m/%Y")
        self.historique_chat = []
        self.contexte_bd = ""

    def _rafraichir_contexte(self):
        donnees = collecter_donnees_bd()
        stats = statistiques_rapides(donnees)

        self.contexte_bd = f"""
=== DONNÉES TEMPS RÉEL — Neo-Sousse 2030 — {self.date_aujourd_hui} ===

CAPTEURS:
{stats["total_capteurs"]} total | {stats["capteurs_actifs"]} actifs | {stats["capteurs_hs"]} hors service

INTERVENTIONS:
{stats["total_interventions"]} total | {stats["interventions_en_cours"]} en cours

VÉHICULES:
{stats["total_vehicules"]} total | {stats["vehicules_en_route"]} en route | {stats["vehicules_en_panne"]} en panne

CITOYENS:
{stats["total_citoyens"]} citoyens | score moyen: {stats["score_moyen_citoyens"]}/100

MESURES:
moyenne={stats["moyenne_mesures"]} | max={stats["max_mesure"]} | min={stats["min_mesure"]}

DONNÉES COMPLÈTES:
{json.dumps(donnees, ensure_ascii=False, default=str, indent=2)[:3000]}
"""

    def rapport_journalier(self) -> str:
        donnees = collecter_donnees_bd()
        stats = statistiques_rapides(donnees)

        prompt = f"""
Génère un rapport journalier professionnel de la ville intelligente Neo-Sousse 2030 pour le {self.date_aujourd_hui}.

Données du jour :
- Capteurs : {stats["total_capteurs"]} total
  * Actifs : {stats["capteurs_actifs"]}
  * Hors service : {stats["capteurs_hs"]} — zones : {[c.get("zone") for c in stats["capteurs_hs_details"]]}
  * Signalés : {stats["capteurs_signales"]}
  * En maintenance : {stats["capteurs_maintenance"]}

- Interventions : {stats["total_interventions"]} total
  * En cours : {stats["interventions_en_cours"]}
  * Terminées : {stats["interventions_terminees"]}

- Mesures :
  * Moyenne : {stats["moyenne_mesures"]}
  * Max : {stats["max_mesure"]}
  * Min : {stats["min_mesure"]}

- Véhicules :
  * En route : {stats["vehicules_en_route"]}
  * En panne : {stats["vehicules_en_panne"]}

- Citoyens :
  * Score écologique moyen : {stats["score_moyen_citoyens"]}/100

Format attendu :
1. Résumé exécutif
2. Alertes critiques
3. Points positifs
4. Recommandations
"""

        return appeler_openrouter_prompt(prompt, max_tokens=900, temperature=0.7)

    def suggestions_actions(self) -> list:
        donnees = collecter_donnees_bd()
        stats = statistiques_rapides(donnees)

        suggestions = []

        for c in stats["capteurs_hs_details"]:
            suggestions.append({
                "priorite": "haute",
                "type": "capteur",
                "message": (
                    f"Intervention urgente recommandée sur capteur ID={c.get('id')} "
                    f"(zone {c.get('zone')}) : hors service, maintenance ou remplacement requis."
                )
            })

        for v in stats["vehicules_panne_details"]:
            suggestions.append({
                "priorite": "haute",
                "type": "vehicule",
                "message": (
                    f"Dépannage requis pour véhicule ID={v.get('id')} "
                    f"(type: {v.get('type')}) : en panne, bloquer les nouvelles assignations."
                )
            })

        if stats["interventions_en_cours"] > 3:
            suggestions.append({
                "priorite": "moyenne",
                "type": "intervention",
                "message": (
                    f"{stats['interventions_en_cours']} interventions en cours — "
                    f"vérifier la charge des techniciens et réaffecter si nécessaire."
                )
            })

        if stats["score_moyen_citoyens"] < 50:
            suggestions.append({
                "priorite": "moyenne",
                "type": "citoyen",
                "message": (
                    f"Score écologique moyen bas ({stats['score_moyen_citoyens']}/100) — "
                    f"lancer une campagne de sensibilisation environnementale."
                )
            })

        if stats["moyenne_mesures"] > 80:
            suggestions.append({
                "priorite": "haute",
                "type": "mesure",
                "message": (
                    f"Moyenne des mesures élevée ({stats['moyenne_mesures']}) — "
                    f"dépassement de seuil potentiel, vérifier la qualité de l'air."
                )
            })

        if not suggestions:
            suggestions.append({
                "priorite": "basse",
                "type": "info",
                "message": "Tous les systèmes fonctionnent normalement. Aucune action requise."
            })

        return suggestions

    def valider_transition_automate(self, entite: str, etat_actuel: str, evenement: str, etat_suivant: str) -> dict:
        transitions_valides = {
            "capteur": {
                ("INACTIF", "activer", "ACTIF"),
                ("ACTIF", "signaler", "SIGNALE"),
                ("SIGNALE", "maintenir", "EN_MAINTENANCE"),
                ("EN_MAINTENANCE", "declarer_hs", "HORS_SERVICE"),
            },
            "intervention": {
                ("DEMANDE", "assigner_tech1", "TECH1_ASSIGNE"),
                ("TECH1_ASSIGNE", "valider_tech2", "TECH2_VALIDE"),
                ("TECH2_VALIDE", "valider_ia", "IA_VALIDE"),
                ("IA_VALIDE", "terminer", "TERMINE"),
            },
            "vehicule": {
                ("STATIONNE", "demarrer", "EN_ROUTE"),
                ("EN_ROUTE", "panne", "EN_PANNE"),
                ("EN_ROUTE", "arriver", "ARRIVE"),
                ("EN_PANNE", "arriver", "ARRIVE"),
            },
        }

        entite_lower = entite.lower()
        transition = (
            normaliser_statut(etat_actuel),
            evenement,
            normaliser_statut(etat_suivant),
        )

        transitions_entite = transitions_valides.get(entite_lower, set())
        est_valide_localement = transition in transitions_entite

        transitions_lisibles = [
            f"{a} --[{e}]--> {b}"
            for a, e, b in transitions_entite
        ]

        prompt = f"""
Dans le système Smart City Neo-Sousse 2030, évalue cette transition d'automate.

Entité : {entite}
État actuel : {etat_actuel}
Événement : {evenement}
État suivant : {etat_suivant}

Transitions valides pour cette entité :
{json.dumps(transitions_lisibles, ensure_ascii=False, indent=2)}

Résultat de la vérification locale :
{"VALIDE" if est_valide_localement else "INVALIDE"}

Réponds uniquement en JSON strict :
{{
  "valide": true ou false,
  "justification": "explication courte"
}}
"""

        reponse = appeler_openrouter_prompt(prompt, max_tokens=250, temperature=0.2)

        try:
            match = re.search(r"\{.*\}", reponse, re.DOTALL)
            if match:
                result = json.loads(match.group())
            else:
                result = {
                    "valide": est_valide_localement,
                    "justification": reponse,
                }
        except Exception:
            result = {
                "valide": est_valide_localement,
                "justification": reponse,
            }

        result["entite"] = entite
        result["transition"] = f"{etat_actuel} --[{evenement}]--> {etat_suivant}"
        result["verification_locale"] = est_valide_localement

        return result

    def chat(self, question: str) -> str:
        if len(self.historique_chat) % 10 == 0:
            self._rafraichir_contexte()

        self.historique_chat.append({"role": "user", "content": question})

        reponse = appeler_openrouter(
            historique=self.historique_chat,
            contexte_bd=self.contexte_bd,
            max_tokens=800,
            temperature=0.7,
        )

        self.historique_chat.append({"role": "assistant", "content": reponse})

        if len(self.historique_chat) > 20:
            self.historique_chat = self.historique_chat[-20:]

        return reponse

    def get_stats(self) -> dict:
        donnees = collecter_donnees_bd()
        stats = statistiques_rapides(donnees)
        stats["date"] = self.date_aujourd_hui

        stats.pop("capteurs_hs_details", None)
        stats.pop("vehicules_panne_details", None)

        return stats

    def get_donnees_completes(self) -> dict:
        donnees = collecter_donnees_bd()

        for table in donnees.values():
            if isinstance(table, list):
                for row in table:
                    for key, val in row.items():
                        if isinstance(val, (datetime.date, datetime.datetime)):
                            row[key] = str(val)

        return donnees


# ══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE — TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from db_config import test_connection

    print("\n" + "=" * 60)
    print("MODULE IA GÉNÉRATIVE — Smart City Neo-Sousse 2030")
    print("Propulsé par OpenRouter")
    print("=" * 60)

    if not test_connection():
        print("PostgreSQL non disponible.")
        sys.exit(1)

    ia = IAGenerative()

    print("\nRAPPORT JOURNALIER")
    print("-" * 55)
    print(ia.rapport_journalier())

    print("\nSUGGESTIONS D'ACTIONS")
    print("-" * 55)
    for s in ia.suggestions_actions():
        print(f"[{s['priorite'].upper()}] {s['message']}")

    print("\nSTATISTIQUES")
    print("-" * 55)
    print(json.dumps(ia.get_stats(), indent=2, ensure_ascii=False))