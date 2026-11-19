"""
Generateur de rapports IA — Smart City Neo-Sousse 2030
Fonctionne AVEC ou SANS base de donnees (mode simule)
Lancez : python ia/generer_rapports_ollama.py  (nécessite Ollama)
"""

import requests
from datetime import datetime

OLLAMA_URL   = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "mistral"

# ─────────────────────────────────────────
# DONNEES SIMULEES (si pas de BD)
# ─────────────────────────────────────────
DONNEES_SIMULEES = {
    "capteurs": [
        {"id": 1,  "type": "pollution", "zone": "Zone Nord",       "statut": "ACTIF",        "taux_erreur": 2.1},
        {"id": 2,  "type": "pollution", "zone": "Zone Sud",        "statut": "ACTIF",        "taux_erreur": 1.5},
        {"id": 3,  "type": "temperature","zone": "Zone Centre",    "statut": "HORS_SERVICE", "taux_erreur": 15.0},
        {"id": 4,  "type": "humidite",  "zone": "Zone Industrielle","statut": "EN_MAINTENANCE","taux_erreur": 8.3},
        {"id": 5,  "type": "pollution", "zone": "Zone Nord",       "statut": "ACTIF",        "taux_erreur": 0.5},
        {"id": 6,  "type": "bruit",     "zone": "Zone Centre",     "statut": "ACTIF",        "taux_erreur": 3.2},
        {"id": 452,"type": "pollution", "zone": "Zone Industrielle","statut": "SIGNALE",      "taux_erreur": 15.0},
    ],
    "mesures": [
        {"zone": "Zone Nord",        "pollution": 72.3, "date": "2026-03-15"},
        {"zone": "Zone Sud",         "pollution": 38.1, "date": "2026-03-15"},
        {"zone": "Zone Centre",      "pollution": 55.7, "date": "2026-03-15"},
        {"zone": "Zone Industrielle","pollution": 91.4, "date": "2026-03-15"},
    ],
    "interventions": [
        {"id": 1, "statut": "TECH1_ASSIGNE", "zone": "Zone Nord",        "duree_h": 12},
        {"id": 2, "statut": "DEMANDE",       "zone": "Zone Industrielle", "duree_h": 31},
        {"id": 3, "statut": "IA_VALIDE",     "zone": "Zone Centre",       "duree_h": 6},
    ],
    "citoyens": [
        {"nom": "Ahmed Ben Ali",    "zone": "Zone Nord",   "score_ecolo": 87},
        {"nom": "Salma Trabelsi",   "zone": "Zone Sud",    "score_ecolo": 92},
        {"nom": "Mohamed Khelifi",  "zone": "Zone Centre", "score_ecolo": 75},
        {"nom": "Fatma Mansouri",   "zone": "Zone Nord",   "score_ecolo": 64},
    ]
}


# ─────────────────────────────────────────
# APPEL OLLAMA
# ─────────────────────────────────────────
def appeler_ollama(system_prompt, user_prompt):
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ]
        }, timeout=120)
        resp.raise_for_status()
        return resp.json()["message"]["content"]
    except requests.exceptions.ConnectionError:
        return "[ERREUR] Ollama non lance. Tapez 'ollama serve' dans un terminal."
    except Exception as e:
        return "[ERREUR] " + str(e)


# ═══════════════════════════════════════════════════════
# RAPPORT 1 — QUALITE DE L'AIR
# ═══════════════════════════════════════════════════════
def rapport_qualite_air(date=None):
    date   = date or datetime.today().strftime("%Y-%m-%d")
    seuil  = 50
    mesures = DONNEES_SIMULEES["mesures"]
    zones_depassees = [m for m in mesures if m["pollution"] > seuil]

    donnees = "\n".join(
        "  * {:<22} pollution = {} ug/m3  {}".format(
            m["zone"], m["pollution"],
            "ALERTE !" if m["pollution"] > seuil else "OK"
        )
        for m in sorted(mesures, key=lambda x: x["pollution"], reverse=True)
    )

    return appeler_ollama(
        "Tu es le systeme IA de la plateforme Smart City Neo-Sousse 2030.\n"
        "Tu rediges des rapports officiels sur la qualite de l'air.\n"
        "Format obligatoire :\n"
        "  RAPPORT QUALITE DE L'AIR — [DATE]\n"
        "  ─────────────────────────────────\n"
        "  RESUME : ...\n"
        "  DONNEES PAR ZONE : ...\n"
        "  ALERTES : ...\n"
        "  RECOMMANDATION : ...\n"
        "Reponds en francais.",

        "Genere le rapport qualite de l'air du {}.\n\n"
        "Mesures enregistrees :\n{}\n\n"
        "Seuil OMS : {} ug/m3 | Zones en alerte : {}/{}".format(
            date, donnees, seuil,
            len(zones_depassees), len(mesures)
        )
    )


# ═══════════════════════════════════════════════════════
# RAPPORT 2 — ETAT DES CAPTEURS
# ═══════════════════════════════════════════════════════
def rapport_etat_capteurs():
    capteurs = DONNEES_SIMULEES["capteurs"]
    total    = len(capteurs)

    stats = {}
    for c in capteurs:
        stats[c["statut"]] = stats.get(c["statut"], 0) + 1

    critiques = [c for c in capteurs if c["statut"] == "HORS_SERVICE"]
    signales  = [c for c in capteurs if c["taux_erreur"] > 10]

    stats_str = "\n".join(
        "  * {:<20} {} capteurs ({}%)".format(
            k, v, round(v/total*100)
        )
        for k, v in sorted(stats.items(), key=lambda x: x[1], reverse=True)
    )

    crit_str = "\n".join(
        "  * Capteur C-{} | Zone: {} | Type: {} | Taux erreur: {}%".format(
            c["id"], c["zone"], c["type"], c["taux_erreur"]
        )
        for c in critiques
    ) or "  Aucun capteur hors service."

    return appeler_ollama(
        "Tu es le systeme IA de la plateforme Smart City Neo-Sousse 2030.\n"
        "Tu generes des rapports d'etat sur l'infrastructure des capteurs urbains.\n"
        "Identifie les priorites d'intervention. Reponds en francais.",

        "Rapport d'etat des capteurs — Total : {} capteurs.\n\n"
        "Repartition par statut :\n{}\n\n"
        "Capteurs hors service :\n{}\n\n"
        "Capteurs avec taux erreur > 10% : {} capteur(s)\n\n"
        "Calcule le taux de disponibilite et propose un plan d'action.".format(
            total, stats_str, crit_str, len(signales)
        )
    )


# ═══════════════════════════════════════════════════════
# RAPPORT 3 — INTERVENTIONS EN COURS
# ═══════════════════════════════════════════════════════
def rapport_interventions():
    interventions = DONNEES_SIMULEES["interventions"]
    retards       = [i for i in interventions if i["duree_h"] > 24]

    details = "\n".join(
        "  * Intervention #{} | Statut: {:<18} | Zone: {} | Duree: {}h {}".format(
            i["id"], i["statut"], i["zone"], i["duree_h"],
            "⚠ RETARD" if i["duree_h"] > 24 else ""
        )
        for i in interventions
    )

    return appeler_ollama(
        "Tu es le systeme IA de la plateforme Smart City Neo-Sousse 2030.\n"
        "Tu generes des rapports de suivi des interventions techniques.\n"
        "Identifie les retards et urgences. Reponds en francais.",

        "Rapport interventions en cours — {} active(s) | {} en retard (>24h)\n\n"
        "Detail :\n{}\n\n"
        "Analyse les retards et propose des actions prioritaires.".format(
            len(interventions), len(retards), details
        )
    )


# ═══════════════════════════════════════════════════════
# RAPPORT 4 — SCORE ECOLOGIQUE
# ═══════════════════════════════════════════════════════
def rapport_score_ecologique():
    citoyens = DONNEES_SIMULEES["citoyens"]
    scores   = [c["score_ecolo"] for c in citoyens]
    moy      = round(sum(scores) / len(scores), 1)
    objectif = 85

    details = "\n".join(
        "  * {:<25} Zone: {:<20} Score: {}/100 {}".format(
            c["nom"], c["zone"], c["score_ecolo"],
            "✓" if c["score_ecolo"] >= objectif else "↓"
        )
        for c in sorted(citoyens, key=lambda x: x["score_ecolo"], reverse=True)
    )

    return appeler_ollama(
        "Tu es le systeme IA de la plateforme Smart City Neo-Sousse 2030.\n"
        "Tu generes des rapports sur les scores ecologiques des citoyens.\n"
        "Compare avec l'objectif 2030. Reponds en francais.",

        "Rapport score ecologique — Date: {}\n\n"
        "Score moyen : {}/100 | Objectif 2030 : {}/100\n"
        "Ecart avec objectif : {}\n\n"
        "Detail par citoyen :\n{}\n\n"
        "Analyse l'ecart et propose des actions pour atteindre l'objectif.".format(
            datetime.today().strftime("%d/%m/%Y"),
            moy, objectif,
            "{:+.1f}".format(moy - objectif),
            details
        )
    )


# ═══════════════════════════════════════════════════════
# SUGGESTION — CAPTEUR C-452
# ═══════════════════════════════════════════════════════
def suggerer_actions_capteur(capteur_id=452):
    capteur = next(
        (c for c in DONNEES_SIMULEES["capteurs"] if c["id"] == capteur_id),
        None
    )
    if not capteur:
        return "Capteur C-{} introuvable.".format(capteur_id)

    return appeler_ollama(
        "Tu es le systeme de recommandation IA de Smart City Neo-Sousse 2030.\n"
        "Propose exactement 3 actions correctives pour un capteur defaillant.\n"
        "Format OBLIGATOIRE :\n"
        "  ACTION 1 — PRIORITE : HAUTE\n"
        "  → Intervention : ...\n"
        "  → Justification : ...\n"
        "  → Delai : ...\n"
        "Reponds en francais.",

        "Analyse ce capteur et propose 3 actions :\n\n"
        "C-{id} | Type: {type} | Zone: {zone} | "
        "Statut: {statut} | Taux erreur: {taux_erreur}%\n\n"
        "Seuils : taux erreur > 10% = critique".format(**capteur)
    )


# ═══════════════════════════════════════════════════════
# RAPPORT COMPLET (tous les rapports d'un coup)
# ═══════════════════════════════════════════════════════
def generer_tous_les_rapports():
    date = datetime.today().strftime("%Y-%m-%d")
    sep  = "=" * 55

    rapports = [
        ("QUALITE DE L'AIR",    rapport_qualite_air(date)),
        ("ETAT DES CAPTEURS",   rapport_etat_capteurs()),
        ("INTERVENTIONS",       rapport_interventions()),
        ("SCORE ECOLOGIQUE",    rapport_score_ecologique()),
        ("SUGGESTION C-452",    suggerer_actions_capteur(452)),
    ]

    print("\n" + sep)
    print("  RAPPORTS IA — Smart City Neo-Sousse 2030")
    print("  Generes le {} avec Ollama/{}".format(
        datetime.today().strftime("%d/%m/%Y %H:%M"), OLLAMA_MODEL))
    print(sep)

    for titre, contenu in rapports:
        print("\n[ {} ]".format(titre))
        print("-" * 40)
        print(contenu)
        print()

    print(sep)
    print("  {} rapports generes avec succes.".format(len(rapports)))
    print(sep)


# ═══════════════════════════════════════════════════════
# MENU INTERACTIF
# ═══════════════════════════════════════════════════════
def menu():
    sep = "=" * 50
    while True:
        print("\n" + sep)
        print("  GENERATEUR DE RAPPORTS — Neo-Sousse 2030")
        print(sep)
        print("  1. Rapport qualite de l'air")
        print("  2. Rapport etat des capteurs")
        print("  3. Rapport interventions en cours")
        print("  4. Rapport score ecologique")
        print("  5. Suggestion actions capteur C-452")
        print("  6. Generer TOUS les rapports")
        print("  0. Quitter")
        print(sep)

        choix = input("  Votre choix : ").strip()

        if choix == "1":
            date = input("  Date (YYYY-MM-DD) ou Entree pour aujourd'hui : ").strip()
            print("\nGeneration en cours...\n")
            print(rapport_qualite_air(date or None))

        elif choix == "2":
            print("\nGeneration en cours...\n")
            print(rapport_etat_capteurs())

        elif choix == "3":
            print("\nGeneration en cours...\n")
            print(rapport_interventions())

        elif choix == "4":
            print("\nGeneration en cours...\n")
            print(rapport_score_ecologique())

        elif choix == "5":
            cid = input("  ID du capteur (defaut: 452) : ").strip()
            print("\nGeneration en cours...\n")
            print(suggerer_actions_capteur(int(cid) if cid else 452))

        elif choix == "6":
            print("\nGeneration de tous les rapports...\n")
            generer_tous_les_rapports()

        elif choix == "0":
            print("\n  Au revoir !\n")
            break
        else:
            print("  Choix invalide.")


if __name__ == "__main__":
    menu()