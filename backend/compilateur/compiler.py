"""
COMPILER - Point d'entree principal du compilateur NL -> SQL
Smart City Neo-Sousse 2030

Pipeline :
1. Detection des requetes ambigues
2. Detection des intentions metier frequentes
3. Lexer
4. Parser
5. Analyse semantique
6. Generation SQL

Objectif : eviter de generer un SQL faux pour une phrase ambigue.
"""

import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer, Token
from nl_parser import Parser, ParseError, QueryNode
from semantic import SemanticAnalyzer, SemanticResult
from codegen import SQLGenerator


@dataclass
class CompileResult:
    success: bool
    sql: Optional[str]
    nl_input: str
    tokens: List[Token] = field(default_factory=list)
    ast: Optional[QueryNode] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stages: dict = field(default_factory=dict)

    # Gestion des requetes ambigues
    ambiguous: bool = False
    message: Optional[str] = None
    options: List[dict] = field(default_factory=list)

    def __str__(self):
        if self.success:
            lines = [
                "Compilation reussie",
                f"NL  : {self.nl_input}",
                f"SQL : {self.sql}",
            ]
            for warning in self.warnings:
                lines.append(f"Warning : {warning}")
            return "\n".join(lines)

        if self.ambiguous:
            lines = [
                "Requete ambigue",
                f"NL : {self.nl_input}",
                f"Clarification : {self.message}",
            ]
            if self.options:
                lines.append("Options :")
                for index, option in enumerate(self.options, 1):
                    lines.append(f"  {index}. {option.get('label', '')}")
                    if option.get("query"):
                        lines.append(f"     Requete : {option['query']}")
                    if option.get("sql"):
                        lines.append(f"     SQL : {' '.join(option['sql'].split())}")
            return "\n".join(lines)

        lines = ["Echec de compilation", f"NL : {self.nl_input}"]
        for error in self.errors:
            lines.append(f"Erreur : {error}")
        return "\n".join(lines)


class NLCompiler:
    def __init__(self, debug: bool = False):
        self.debug = debug

    def compile(self, nl_query: str) -> CompileResult:
        result = CompileResult(success=False, sql=None, nl_input=nl_query or "")

        if not nl_query or not nl_query.strip():
            result.errors.append("Requete vide.")
            result.message = "Requete vide."
            return result

        # 1) Requetes ambigues : on ne genere pas de SQL au hasard.
        ambiguity = self._detect_ambiguity(nl_query)
        if ambiguity:
            result.ambiguous = True
            result.message = ambiguity["message"]
            result.options = ambiguity.get("options", [])
            return result

        # 2) Intentions metier connues : SQL direct, plus fiable pour le projet.
        direct = self._compile_direct_intent(nl_query)
        if direct:
            sql, warnings, intent = direct
            result.success = True
            result.sql = sql
            result.warnings.extend(warnings)
            result.stages["direct_intent"] = intent

            try:
                result.tokens = Lexer(nl_query).tokenize()
                result.stages["lexer"] = [str(t) for t in result.tokens]
            except Exception:
                pass

            return result

        # 3) Pipeline classique : lexer -> parser -> semantic -> codegen.
        try:
            lexer = Lexer(nl_query)
            tokens = lexer.tokenize()
            result.tokens = tokens
            result.stages["lexer"] = [str(t) for t in tokens]

            if self.debug:
                print(f"\n[LEXER] {len(tokens)} tokens")
                for token in tokens:
                    print(f"  {token}")

        except Exception as e:
            result.errors.append(f"[Lexer] {e}")
            return result

        try:
            parser = Parser(tokens)
            ast = parser.parse()
            result.ast = ast
            result.stages["parser"] = str(ast)

            if self.debug:
                print(f"\n[PARSER] {ast}")

        except ParseError as e:
            result.errors.append(f"[Parser] {e}")
            return result
        except Exception as e:
            result.errors.append(f"[Parser] Erreur inattendue : {e}")
            return result

        try:
            sem = SemanticAnalyzer(ast)
            sem_result: SemanticResult = sem.analyze()
            result.warnings.extend(sem_result.warnings)

            if not sem_result.is_valid:
                result.errors.extend(sem_result.errors)
                return result

            validated_ast = sem_result.corrected_node

        except Exception as e:
            result.errors.append(f"[Semantic] {e}")
            return result

        try:
            generator = SQLGenerator(validated_ast)
            sql = generator.generate()
            result.sql = sql
            result.success = True
            result.stages["codegen"] = sql

        except Exception as e:
            result.errors.append(f"[CodeGen] {e}")

        return result

    def compile_batch(self, queries: List[str]) -> List[CompileResult]:
        return [self.compile(query) for query in queries]

    # ------------------------------------------------------------------
    # Requetes ambigues
    # ------------------------------------------------------------------
    def _detect_ambiguity(self, text: str) -> Optional[dict]:
        q = self._norm(text)
        has_entity = self._has_entity(q)

        if self._contains(q, ["donnees", "data", "tout", "tous", "toutes"]) and not has_entity:
            return {
                "message": "Votre requete est ambigue : quelles donnees voulez-vous afficher ?",
                "options": [
                    {
                        "label": "Afficher les capteurs",
                        "query": "Affiche tous les capteurs",
                        "sql": self._sql_select_table("capteurs"),
                    },
                    {
                        "label": "Afficher les interventions",
                        "query": "Affiche les interventions",
                        "sql": self._sql_select_table("interventions"),
                    },
                    {
                        "label": "Afficher les vehicules",
                        "query": "Liste les vehicules",
                        "sql": self._sql_select_table("vehicules"),
                    },
                    {
                        "label": "Afficher les dernieres mesures",
                        "query": "Affiche les dernieres mesures",
                        "sql": self._sql_last_mesures(10),
                    },
                ],
            }

        if self._contains(q, ["actif", "actifs", "active", "actives"]) and not has_entity:
            return {
                "message": "Le mot 'actifs' peut designer les capteurs, les vehicules ou les interventions.",
                "options": [
                    {
                        "label": "Capteurs actifs",
                        "query": "Affiche tous les capteurs actifs",
                        "sql": self._sql_capteurs_status("ACTIF", False),
                    },
                    {
                        "label": "Vehicules en route",
                        "query": "Liste les vehicules en route",
                        "sql": self._sql_vehicules_status("EN_ROUTE", False),
                    },
                    {
                        "label": "Interventions en cours",
                        "query": "Affiche les interventions en cours",
                        "sql": self._sql_interventions_en_cours(False),
                    },
                ],
            }

        if self._contains(q, ["panne", "pannes"]) and not has_entity:
            return {
                "message": "La panne concerne-t-elle les vehicules ou les capteurs hors service ?",
                "options": [
                    {
                        "label": "Vehicules en panne",
                        "query": "Liste les vehicules en panne",
                        "sql": self._sql_vehicules_status("EN_PANNE", False),
                    },
                    {
                        "label": "Capteurs hors service",
                        "query": "Affiche les capteurs hors service",
                        "sql": self._sql_capteurs_status("HORS_SERVICE", False),
                    },
                    {
                        "label": "Compter les vehicules en panne",
                        "query": "Combien de vehicules sont en panne ?",
                        "sql": self._sql_vehicules_status("EN_PANNE", True),
                    },
                    {
                        "label": "Compter les capteurs hors service",
                        "query": "Combien de capteurs sont hors service ?",
                        "sql": self._sql_capteurs_status("HORS_SERVICE", True),
                    },
                ],
            }

        if self._contains(q, ["probleme", "problemes", "anomalie", "anomalies", "alerte", "alertes"]) and not has_entity:
            return {
                "message": "Le mot 'problemes' est ambigu : voulez-vous les capteurs, vehicules ou interventions ?",
                "options": [
                    {
                        "label": "Capteurs hors service",
                        "query": "Affiche les capteurs hors service",
                        "sql": self._sql_capteurs_status("HORS_SERVICE", False),
                    },
                    {
                        "label": "Vehicules en panne",
                        "query": "Liste les vehicules en panne",
                        "sql": self._sql_vehicules_status("EN_PANNE", False),
                    },
                    {
                        "label": "Interventions non terminees",
                        "query": "Affiche les interventions en cours",
                        "sql": self._sql_interventions_en_cours(False),
                    },
                ],
            }

        if self._contains(q, ["dernier", "derniers", "derniere", "dernieres", "recent", "recents", "recente", "recentes"]) and not has_entity:
            return {
                "message": "Precisez l'entite : dernieres mesures, dernieres interventions ou derniers capteurs ?",
                "options": [
                    {
                        "label": "Dernieres mesures",
                        "query": "Affiche les dernieres mesures",
                        "sql": self._sql_last_mesures(10),
                    },
                    {
                        "label": "Dernieres interventions",
                        "query": "Affiche les dernieres interventions",
                        "sql": self._sql_last_interventions(10),
                    },
                    {
                        "label": "Derniers capteurs installes",
                        "query": "Affiche les derniers capteurs",
                        "sql": self._sql_last_capteurs(10),
                    },
                ],
            }

        if (
            "zone" in q
            and self._contains(q, ["critique", "critiques"])
            and not self._contains(q, ["pollution", "polluee", "polluees", "hors service"])
        ):
            return {
                "message": "Zone critique selon quel critere : pollution, capteurs hors service ou interventions ?",
                "options": [
                    {
                        "label": "Zones les plus polluees",
                        "query": "Affiche les 5 zones les plus polluees",
                        "sql": self._sql_polluted_zones(5),
                    },
                    {
                        "label": "Zones avec le plus de capteurs hors service",
                        "query": "Affiche les zones avec le plus de capteurs hors service",
                        "sql": self._sql_zones_capteurs_hs(5),
                    },
                    {
                        "label": "Zones avec interventions en cours",
                        "query": "Affiche les zones avec interventions en cours",
                        "sql": self._sql_zones_interventions(5),
                    },
                ],
            }

        if (
            "trajet" in q
            and self._contains(q, ["meilleur", "meilleure"])
            and not self._contains(q, ["co2", "carbone", "distance", "duree", "temps"])
        ):
            return {
                "message": "Meilleur trajet selon quel critere : CO2, distance ou duree ?",
                "options": [
                    {
                        "label": "Trajet le plus economique en CO2",
                        "query": "Donne-moi le trajet le plus economique en CO2",
                        "sql": self._sql_trajet_co2(),
                    },
                    {
                        "label": "Trajet le plus court",
                        "query": "Donne-moi le trajet le plus court",
                        "sql": "SELECT trajet_id, distance FROM trajets ORDER BY distance ASC LIMIT 1;",
                    },
                    {
                        "label": "Trajet le plus rapide",
                        "query": "Donne-moi le trajet le plus rapide",
                        "sql": "SELECT trajet_id, duree FROM trajets ORDER BY duree ASC LIMIT 1;",
                    },
                ],
            }

        # "état" sans entité
        if self._contains(q, ["etat", "statut", "status"]) and not has_entity:
            return {
                "message": "De quelle entite voulez-vous voir l'etat ?",
                "options": [
                    {
                        "label": "Etat des capteurs",
                        "query": "Affiche tous les capteurs",
                        "sql": self._sql_select_table("capteurs"),
                    },
                    {
                        "label": "Etat des interventions",
                        "query": "Liste les interventions",
                        "sql": self._sql_select_table("interventions"),
                    },
                    {
                        "label": "Etat des vehicules",
                        "query": "Affiche les vehicules",
                        "sql": self._sql_select_table("vehicules"),
                    },
                ],
            }

        # "liste" sans entité
        if self._contains(q, ["liste", "lister", "affiche", "afficher", "montre", "montrer"]) and not has_entity:
            return {
                "message": "Que voulez-vous lister ?",
                "options": [
                    {
                        "label": "Liste des capteurs",
                        "query": "Liste tous les capteurs",
                        "sql": self._sql_select_table("capteurs"),
                    },
                    {
                        "label": "Liste des citoyens",
                        "query": "Liste tous les citoyens",
                        "sql": self._sql_select_table("citoyens"),
                    },
                    {
                        "label": "Liste des vehicules",
                        "query": "Liste tous les vehicules",
                        "sql": self._sql_select_table("vehicules"),
                    },
                    {
                        "label": "Liste des interventions",
                        "query": "Liste les interventions",
                        "sql": self._sql_select_table("interventions"),
                    },
                ],
            }

        # "rapport" ou "résumé" sans entité
        if self._contains(q, ["rapport", "resume", "bilan", "synthese"]) and not has_entity:
            return {
                "message": "Quel type de rapport voulez-vous ?",
                "options": [
                    {
                        "label": "Rapport capteurs",
                        "query": "Combien de capteurs sont actifs ?",
                        "sql": self._sql_capteurs_status("ACTIF", True),
                    },
                    {
                        "label": "Rapport interventions",
                        "query": "Combien d interventions sont en cours ?",
                        "sql": self._sql_interventions_en_cours(True),
                    },
                    {
                        "label": "Rapport vehicules",
                        "query": "Combien de vehicules sont en route ?",
                        "sql": self._sql_vehicules_status("EN_ROUTE", True),
                    },
                ],
            }

        return None
        
        

    # ------------------------------------------------------------------
    # Intentions metier directes
    # ------------------------------------------------------------------

    def _compile_direct_intent(self, text: str) -> Optional[tuple]:
        q = self._norm(text)
        limit = self._extract_limit(q)

        # TOP zones polluees
        if "zone" in q and self._contains(q, ["pollution", "polluee", "polluees", "pollue"]):
            return self._sql_polluted_zones(limit or 5), [], "zones_polluees"

        # Citoyens avec score ecologique > X
        if self._contains(q, ["citoyen", "citoyens", "habitant", "habitants"]) and "score" in q:
            op = self._extract_operator(q, default=">")
            value = self._extract_number(q, default=80)
            sql = (
                "SELECT nom, score_ecolo AS score\n"
                "FROM citoyens\n"
                f"WHERE score_ecolo {op} {value}\n"
                "ORDER BY score_ecolo DESC;"
            )
            return sql, [], "citoyens_score"

        # Trajet economique en CO2
        if "trajet" in q and self._contains(q, ["co2", "carbone", "emission", "emissions"]):
            return self._sql_trajet_co2(), [
                "Cette requete suppose l'existence de la table trajets(trajet_id, economie_co2)."
            ], "trajet_co2"

        # Capteurs avec taux d'erreur superieur a X
        if "capteur" in q and self._contains(q, ["erreur", "erreurs", "taux"]):
            value = self._extract_number(q, default=10)
            op = self._extract_operator(q, default=">")
            only_active = self._contains(q, ["actif", "actifs"])
            sql = self._sql_capteurs_taux_erreur(op, value, only_active)
            return sql, [], "capteurs_taux_erreur"

        # Comptage ou affichage capteurs par statut
        if "capteur" in q:
            count = self._is_count(q)
            if self._contains(q, ["hors service", "hors_service", "hs", "defaillant", "defaillants"]):
                return self._sql_capteurs_status("HORS_SERVICE", count), [], "capteurs_hors_service"
            if self._contains(q, ["inactif", "inactifs"]):
                return self._sql_capteurs_status("INACTIF", count), [], "capteurs_inactifs"
            if self._contains(q, ["actif", "actifs"]):
                return self._sql_capteurs_status("ACTIF", count), [], "capteurs_actifs"
            if self._contains(q, ["signale", "signales"]):
                return self._sql_capteurs_status("SIGNALE", count), [], "capteurs_signales"
            if self._contains(q, ["maintenance"]):
                return self._sql_capteurs_status("EN_MAINTENANCE", count), [], "capteurs_maintenance"

            zone = self._extract_zone_value(q)
            if zone:
                return self._sql_capteurs_zone(zone, count), [], "capteurs_zone"

        # Interventions
        if self._contains(q, ["intervention", "interventions"]):
            count = self._is_count(q)

            if self._contains(q, ["en cours", "encours", "cours", "active", "actives"]):
                return self._sql_interventions_en_cours(count), [], "interventions_en_cours"

            if self._contains(q, ["termine", "termines", "terminee", "terminees"]):
                return self._sql_interventions_status("TERMINE", count), [], "interventions_terminees"

            if self._contains(q, ["demande"]):
                return self._sql_interventions_status("DEMANDE", count), [], "interventions_demande"

            if self._contains(q, ["dernier", "derniers", "derniere", "dernieres", "recent", "recents"]):
                return self._sql_last_interventions(limit or 10), [], "interventions_recentes"

        # Vehicules
        if self._contains(q, ["vehicule", "vehicules", "voiture", "voitures"]):
            count = self._is_count(q)
            if self._contains(q, ["panne", "pannes"]):
                return self._sql_vehicules_status("EN_PANNE", count), [], "vehicules_panne"
            if self._contains(q, ["route", "en route"]):
                return self._sql_vehicules_status("EN_ROUTE", count), [], "vehicules_route"
            if self._contains(q, ["stationne", "stationnes"]):
                return self._sql_vehicules_status("STATIONNE", count), [], "vehicules_stationnes"
            if self._contains(q, ["arrive", "arrives"]):
                return self._sql_vehicules_status("ARRIVE", count), [], "vehicules_arrives"

        # Mesures
        if self._contains(q, ["mesure", "mesures"]):
            if self._contains(q, ["dernier", "derniers", "derniere", "dernieres", "recent", "recents"]):
                return self._sql_last_mesures(limit or 10), [], "mesures_recentes"

            zone = self._extract_zone_value(q)
            if zone:
                return self._sql_mesures_zone(zone, limit), [], "mesures_zone"

        # Zones simples
        if "zone" in q:
            count = self._is_count(q)
            if count:
                return "SELECT COUNT(DISTINCT zone) AS total\nFROM capteurs;", [], "zones_count"
            return "SELECT DISTINCT zone\nFROM capteurs\nORDER BY zone ASC;", [], "zones_liste"

        return None

    # ------------------------------------------------------------------
    # SQL templates
    # ------------------------------------------------------------------

    def _sql_select_table(self, table: str, count: bool = False, limit: Optional[int] = None) -> str:
        cols = {
            "capteurs": "id, type, zone, statut, date_installation",
            "interventions": "id, capteur_id, technicien1_id, technicien2_id, statut, date",
            "citoyens": "id, nom, score_ecolo, adresse",
            "vehicules": "id, type, trajet_id, statut",
            "mesures": "id, capteur_id, type_mesure, valeur, date",
        }

        if count:
            return f"SELECT COUNT(*) AS total\nFROM {table};"

        sql = f"SELECT {cols.get(table, '*')}\nFROM {table}"
        if limit:
            sql += f"\nLIMIT {limit}"
        return sql + ";"

    def _sql_polluted_zones(self, limit: int = 5) -> str:
        return (
            "SELECT c.zone, AVG(m.valeur) AS pollution_moyenne\n"
            "FROM mesures m\n"
            "JOIN capteurs c ON c.id = m.capteur_id\n"
            "WHERE LOWER(m.type_mesure) LIKE '%pollution%'\n"
            "   OR LOWER(m.type_mesure) LIKE '%air%'\n"
            "GROUP BY c.zone\n"
            "ORDER BY pollution_moyenne DESC\n"
            f"LIMIT {limit};"
        )

    def _sql_zones_capteurs_hs(self, limit: int = 5) -> str:
        return (
            "SELECT zone, COUNT(*) AS nb_capteurs_hors_service\n"
            "FROM capteurs\n"
            "WHERE UPPER(statut) = 'HORS_SERVICE'\n"
            "GROUP BY zone\n"
            "ORDER BY nb_capteurs_hors_service DESC\n"
            f"LIMIT {limit};"
        )

    def _sql_zones_interventions(self, limit: int = 5) -> str:
        return (
            "SELECT c.zone, COUNT(*) AS nb_interventions_en_cours\n"
            "FROM interventions i\n"
            "JOIN capteurs c ON c.id = i.capteur_id\n"
            "WHERE UPPER(i.statut) IN ('DEMANDE', 'TECH1_ASSIGNE', 'TECH2_VALIDE', 'IA_VALIDE', 'EN_COURS')\n"
            "GROUP BY c.zone\n"
            "ORDER BY nb_interventions_en_cours DESC\n"
            f"LIMIT {limit};"
        )

    def _sql_capteurs_status(self, status: str, count: bool = False) -> str:
        if count:
            return (
                "SELECT COUNT(*) AS total\n"
                "FROM capteurs\n"
                f"WHERE UPPER(statut) = '{status}';"
            )

        return (
            "SELECT id, type, zone, statut, date_installation\n"
            "FROM capteurs\n"
            f"WHERE UPPER(statut) = '{status}'\n"
            "ORDER BY id ASC;"
        )

    def _sql_capteurs_zone(self, zone: str, count: bool = False) -> str:
        zone_sql = self._escape_sql(zone)
        if count:
            return (
                "SELECT COUNT(*) AS total\n"
                "FROM capteurs\n"
                f"WHERE LOWER(zone) LIKE LOWER('%{zone_sql}%');"
            )

        return (
            "SELECT id, type, zone, statut, date_installation\n"
            "FROM capteurs\n"
            f"WHERE LOWER(zone) LIKE LOWER('%{zone_sql}%')\n"
            "ORDER BY id ASC;"
        )

    def _sql_capteurs_taux_erreur(self, op: str, value: float, only_active: bool = False) -> str:
        active_filter = "\n  AND UPPER(c.statut) = 'ACTIF'" if only_active else ""
        return (
            "SELECT c.id, c.type, c.zone, c.statut, m.valeur AS taux_erreur\n"
            "FROM capteurs c\n"
            "JOIN mesures m ON m.capteur_id = c.id\n"
            "WHERE LOWER(m.type_mesure) LIKE '%erreur%'"
            f"{active_filter}\n"
            f"  AND m.valeur {op} {value}\n"
            "ORDER BY taux_erreur DESC;"
        )

    def _sql_interventions_status(self, status: str, count: bool = False) -> str:
        if count:
            return (
                "SELECT COUNT(*) AS total\n"
                "FROM interventions\n"
                f"WHERE UPPER(statut) = '{status}';"
            )

        return (
            "SELECT id, capteur_id, technicien1_id, technicien2_id, statut, date\n"
            "FROM interventions\n"
            f"WHERE UPPER(statut) = '{status}'\n"
            "ORDER BY date DESC;"
        )

    def _sql_interventions_en_cours(self, count: bool = False) -> str:
        where = "UPPER(statut) IN ('DEMANDE', 'TECH1_ASSIGNE', 'TECH2_VALIDE', 'IA_VALIDE', 'EN_COURS')"
        if count:
            return f"SELECT COUNT(*) AS total\nFROM interventions\nWHERE {where};"

        return (
            "SELECT id, capteur_id, technicien1_id, technicien2_id, statut, date\n"
            "FROM interventions\n"
            f"WHERE {where}\n"
            "ORDER BY date DESC;"
        )

    def _sql_vehicules_status(self, status: str, count: bool = False) -> str:
        if count:
            return (
                "SELECT COUNT(*) AS total\n"
                "FROM vehicules\n"
                f"WHERE UPPER(statut) = '{status}';"
            )

        return (
            "SELECT id, type, trajet_id, statut\n"
            "FROM vehicules\n"
            f"WHERE UPPER(statut) = '{status}'\n"
            "ORDER BY id ASC;"
        )

    def _sql_last_mesures(self, limit: int = 10) -> str:
        return (
            "SELECT id, capteur_id, type_mesure, valeur, date\n"
            "FROM mesures\n"
            "ORDER BY date DESC\n"
            f"LIMIT {limit};"
        )

    def _sql_last_interventions(self, limit: int = 10) -> str:
        return (
            "SELECT id, capteur_id, technicien1_id, technicien2_id, statut, date\n"
            "FROM interventions\n"
            "ORDER BY date DESC\n"
            f"LIMIT {limit};"
        )

    def _sql_last_capteurs(self, limit: int = 10) -> str:
        return (
            "SELECT id, type, zone, statut, date_installation\n"
            "FROM capteurs\n"
            "ORDER BY date_installation DESC\n"
            f"LIMIT {limit};"
        )

    def _sql_mesures_zone(self, zone: str, limit: Optional[int] = None) -> str:
        zone_sql = self._escape_sql(zone)
        sql = (
            "SELECT m.id, m.capteur_id, c.zone, m.type_mesure, m.valeur, m.date\n"
            "FROM mesures m\n"
            "JOIN capteurs c ON c.id = m.capteur_id\n"
            f"WHERE LOWER(c.zone) LIKE LOWER('%{zone_sql}%')\n"
            "ORDER BY m.date DESC"
        )
        if limit:
            sql += f"\nLIMIT {limit}"
        return sql + ";"

    def _sql_trajet_co2(self) -> str:
        return (
            "SELECT trajet_id, economie_co2\n"
            "FROM trajets\n"
            "ORDER BY economie_co2 DESC\n"
            "LIMIT 1;"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _norm(text: str) -> str:
        text = text or ""
        text = text.lower()
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = text.replace("’", "'")
        text = re.sub(r"[_\-]+", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _contains(q: str, words: List[str]) -> bool:
        return any(word in q for word in words)

    @staticmethod
    def _escape_sql(value: str) -> str:
        return str(value).replace("'", "''")

    def _has_entity(self, q: str) -> bool:
        return self._contains(q, [
            "capteur", "capteurs",
            "intervention", "interventions",
            "citoyen", "citoyens", "habitant", "habitants",
            "vehicule", "vehicules", "voiture", "voitures",
            "mesure", "mesures",
            "zone", "zones",
            "trajet", "trajets",
        ])

    @staticmethod
    def _is_count(q: str) -> bool:
        return any(word in q for word in ["combien", "nombre", "compte", "compter", "total"])

    @staticmethod
    def _extract_limit(q: str) -> Optional[int]:
        patterns = [
            r"\b(?:les?|top|premiers?)\s+(\d+)\b",
            r"\blimite\s+(\d+)\b",
            r"\b(\d+)\s+(?:capteurs?|zones?|mesures?|interventions?|vehicules?|citoyens?)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, q)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _extract_number(q: str, default: float = 0) -> float:
        match = re.search(r"\b\d+(?:\.\d+)?\b", q)
        if not match:
            return default
        value = match.group()
        return float(value) if "." in value else int(value)

    @staticmethod
    def _extract_operator(q: str, default: str = "=") -> str:
        if ">=" in q or "superieur ou egal" in q or "au moins" in q:
            return ">="
        if "<=" in q or "inferieur ou egal" in q or "au plus" in q:
            return "<="
        if ">" in q or "superieur" in q or "plus grand" in q or "depasse" in q:
            return ">"
        if "<" in q or "inferieur" in q or "plus petit" in q:
            return "<"
        if "=" in q or "egal" in q or "vaut" in q:
            return "="
        return default

    @staticmethod
    def _extract_zone_value(q: str) -> Optional[str]:
        patterns = [
            r"\bzone\s+([a-z0-9_ ]{2,30})",
            r"\bsecteur\s+([a-z0-9_ ]{2,30})",
        ]
        stop_words = {
            "avec", "ou", "qui", "dont", "ayant", "en", "de", "des",
            "les", "plus", "polluees", "pollues", "pollution", "par", "pour",
        }
        for pattern in patterns:
            match = re.search(pattern, q)
            if not match:
                continue
            value = match.group(1).strip()
            parts = []
            for part in value.split():
                if part in stop_words:
                    break
                parts.append(part)
            if parts:
                return " ".join(parts)
        return None


def interactive_mode():
    compiler = NLCompiler(debug=False)
    print('=' * 60)
    print('  Compilateur NL -> SQL - Smart City Neo-Sousse 2030')
    print('  exit pour quitter | debug pour mode debug')
    print('=' * 60)

    while True:
        try:
            query = input('NL> ').strip()
        except (EOFError, KeyboardInterrupt):
            print('Au revoir.')
            break

        if not query:
            continue
        if query.lower() in ('exit', 'quit', 'quitter'):
            break
        if query.lower() == 'debug':
            compiler.debug = not compiler.debug
            print('Debug:', 'ON' if compiler.debug else 'OFF')
            continue

        result = compiler.compile(query)

        # ── Requête ambiguë ──
        if result.ambiguous and result.options:
            print()
            print('  Requete ambigue :', result.message)
            print()
            for i, opt in enumerate(result.options, 1):
                print(f"  [{i}] {opt.get('label','')}")
                if opt.get('query'):
                    print(f"      -> {opt['query']}")
                if opt.get('sql'):
                    print(f"      SQL : {' '.join(opt['sql'].split())}")
            print()
            print(f"  Choisissez [1-{len(result.options)}] ou 'non' : ", end='')
            try:
                c = input().strip()
                if c.lower() in ('non', 'n', ''):
                    print('  Annule.\n')
                    continue
                idx = int(c) - 1
                chosen = result.options[idx]
                print(f"\n  Choisi : {chosen.get('label','')}")
                sql = chosen.get('sql') or compiler.compile(chosen.get('query','')).sql
                if sql:
                    print(f"  SQL : {' '.join(sql.split())}")
            except:
                print('  Annule.')
            print()
            continue

        # ── Résultat normal ──
        print(result)
        print()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        print(NLCompiler(debug=True).compile(q))
    else:
        interactive_mode()
