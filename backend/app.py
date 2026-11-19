"""
APP.PY — Serveur Flask REST API & WebSockets — Smart City Neo-Sousse 2030
Port : 5000 | WebSockets local poussant les données en temps réel
"""

import sys
import os
import json
import datetime
import decimal
import random
import time
import threading

# ── Configuration des chemins ──
base = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(base)
sys.path.insert(0, base)
sys.path.insert(0, parent)
sys.path.insert(0, os.path.join(base, 'bdd'))
sys.path.insert(0, os.path.join(base, 'compilateur'))

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from ia_module import IAGenerative, collecter_donnees_bd
from db_config import get_cursor, test_connection
from db_executor import DBExecutor

# Instance globale de l'exécuteur DB pour le compilateur
db_exec = DBExecutor()

# ── Initialisation de l'application ──
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Instance globale du module IA
ia = IAGenerative()

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(CustomEncoder, self).default(obj)

def api_response(data, code=200):
    """Helper for consistent JSON responses with custom encoding and CORS."""
    response = make_response(json.dumps(data, cls=CustomEncoder), code)
    response.headers['Content-Type'] = 'application/json'
    return response

# ── Background Task: Real-time Updates ──

def background_metrics_worker():
    """
    Tâche de fond qui pousse les métriques et alertes vers le frontend via Socket.IO.
    """
    last_report_time = 0
    print("🚀 Background metrics worker started.")
    
    while True:
        try:
            # 1. Collecte des données
            donnees = collecter_donnees_bd()
            stats = ia.get_stats()
            
            # Pousser les métriques générales
            socketio.emit('metrics_update', json.loads(json.dumps(stats, cls=CustomEncoder)))
            
            # 2. Vérification des alertes instantanées
            capteurs = donnees.get('capteurs', [])
            for c in capteurs:
                if c.get('statut') == 'HORS_SERVICE':
                    socketio.emit('alert', {
                        "type": "capteur",
                        "id": c['id'],
                        "message": f"🚨 Alerte : Capteur {c['id']} (Zone: {c['zone']}) est HORS SERVICE !"
                    })
            
            interventions = donnees.get('interventions', [])
            now = datetime.datetime.now()
            for i in interventions:
                if i.get('statut') != 'TERMINE':
                    # Simulation d'alerte > 24h si la date est ancienne
                    date_demande = i.get('date')
                    if date_demande:
                        try:
                            # Tentative de parser si c'est un string
                            if isinstance(date_demande, str):
                                dt = datetime.datetime.fromisoformat(date_demande)
                            else:
                                dt = date_demande
                            if (now - dt).total_seconds() > 86400: # 24h
                                socketio.emit('alert', {
                                    "type": "intervention",
                                    "id": i['id'],
                                    "message": f"⏳ Retard : L'intervention {i['id']} dépasse les 24h !"
                                })
                        except: pass

            # 3. Rapport IA automatique toutes les heures (simulé à 2 min pour démo si besoin, ou réel)
            if time.time() - last_report_time > 3600: # 1 heure
                print("🤖 Génération du rapport IA horaire...")
                rapport = ia.rapport_journalier()
                socketio.emit('ai_report', {
                    "rapport": rapport,
                    "timestamp": datetime.datetime.now().isoformat()
                })
                last_report_time = time.time()

        except Exception as e:
            print(f"❌ Error in background worker: {e}")
        
        time.sleep(10) # Mise à jour toutes les 10 secondes

# Démarrage du thread de fond
threading.Thread(target=background_metrics_worker, daemon=True).start()

# ── API Routes ──

@app.route('/api/dashboard')
def api_dashboard():
    try:
        stats = ia.get_stats()
        return api_response({"success": True, **stats})
    except Exception as e:
        return api_response({"success": False, "error": str(e)}, 500)

@app.route('/api/capteurs')
def api_capteurs():
    try:
        donnees = collecter_donnees_bd()
        return api_response({"success": True, "capteurs": donnees.get('capteurs', [])})
    except Exception as e:
        return api_response({"success": False, "error": str(e)}, 500)

@app.route('/api/interventions')
def api_interventions():
    try:
        donnees = collecter_donnees_bd()
        return api_response({"success": True, "interventions": donnees.get('interventions', [])})
    except Exception as e:
        return api_response({"success": False, "error": str(e)}, 500)

@app.route('/api/mesures')
def api_mesures():
    try:
        donnees = collecter_donnees_bd()
        return api_response({"success": True, "mesures": donnees.get('mesures', [])})
    except Exception as e:
        return api_response({"success": False, "error": str(e)}, 500)

@app.route('/api/citoyens')
def api_citoyens():
    try:
        donnees = collecter_donnees_bd()
        return api_response({"success": True, "citoyens": donnees.get('citoyens', [])})
    except Exception as e:
        return api_response({"success": False, "error": str(e)}, 500)

@app.route('/api/vehicules')
def api_vehicules():
    try:
        donnees = collecter_donnees_bd()
        return api_response({"success": True, "vehicules": donnees.get('vehicules', [])})
    except Exception as e:
        return api_response({"success": False, "error": str(e)}, 500)

@app.route('/api/rapport')
def api_rapport():
    try:
        texte = ia.rapport_journalier()
        return api_response({"success": True, "rapport": texte, "date": ia.date_aujourd_hui})
    except Exception as e:
        return api_response({"success": False, "error": str(e)}, 500)

@app.route('/api/suggestions')
def api_suggestions():
    try:
        liste = ia.suggestions_actions()
        return api_response({"success": True, "suggestions": liste})
    except Exception as e:
        return api_response({"success": False, "error": str(e)}, 500)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json() or {}
        reponse = ia.chat(data.get('question', 'Bonjour'))
        return api_response({"success": True, "reponse": reponse})
    except Exception as e:
        return api_response({"success": False, "error": str(e)}, 500)

# Nouvelle route pour déclencher manuellement une mise à jour d'automate et notifier via Socket
@app.route('/api/notify-update', methods=['POST'])
def api_notify_update():
    data = request.get_json() or {}
    # Notifier tous les clients d'un changement de statut
    socketio.emit('status_change', data)
    return api_response({"success": True})

@app.route('/api/compiler', methods=['POST'])
def api_compiler():
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()

        if not query:
            return api_response({
                "success": False,
                "ambiguous": False,
                "sql": "-- Requête vide --",
                "errors": ["Requête vide"],
                "message": "Requête vide",
                "debug": {}
            }, 400)

        # 1. Compiler d'abord, sans exécuter
        compile_result = db_exec.compiler.compile(query)

        debug_info = {
            "tokens": [str(t) for t in compile_result.tokens],
            "ast": str(compile_result.ast) if compile_result.ast else "",
            "stages": compile_result.stages
        }

        # 2. Cas spécial : requête ambiguë
        if getattr(compile_result, "ambiguous", False):
            return api_response({
                "success": False,
                "ambiguous": True,
                "message": compile_result.message or "Requête ambiguë",
                "options": compile_result.options,
                "sql": "-- Requête ambiguë : choisissez une interprétation --",
                "errors": [],
                "warnings": compile_result.warnings,
                "nl_input": query,
                "debug": debug_info
            })

        # 3. Cas erreur de compilation réelle
        if not compile_result.success:
            return api_response({
                "success": False,
                "ambiguous": False,
                "message": "Erreur de compilation",
                "sql": "-- Erreur de génération --",
                "errors": compile_result.errors,
                "warnings": compile_result.warnings,
                "nl_input": query,
                "debug": debug_info
            })

        # 4. Si SQL valide, on exécute dans PostgreSQL
        result = db_exec.execute_nl(query)

        if result.success:
            return api_response({
                "success": True,
                "ambiguous": False,
                "sql": result.sql,
                "rows": result.rows,
                "row_count": result.row_count,
                "nl_input": result.nl_input,
                "errors": [],
                "warnings": compile_result.warnings,
                "debug": debug_info
            })

        return api_response({
            "success": False,
            "ambiguous": False,
            "message": "Erreur d'exécution SQL",
            "sql": result.sql or compile_result.sql,
            "errors": [result.error],
            "warnings": compile_result.warnings,
            "nl_input": result.nl_input,
            "debug": debug_info
        })

    except Exception as e:
        return api_response({
            "success": False,
            "ambiguous": False,
            "message": "Erreur serveur",
            "sql": "-- Erreur serveur --",
            "errors": [str(e)],
            "debug": {}
        }, 500)
if __name__ == '__main__':
    test_connection()
    # Utilisation de socketio.run pour supporter eventlet/websockets
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
