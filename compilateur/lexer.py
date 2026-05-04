"""
LEXER - Tokenisation des requêtes en langage naturel
Smart City Neo-Sousse 2030

Ce lexer transforme une phrase française en tokens simples.
La gestion avancée des intentions et ambiguïtés est faite dans compiler.py.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List


class TokenType(Enum):
    # Actions
    SHOW = auto()
    COUNT = auto()
    FIND = auto()
    GET = auto()

    # Entités
    CAPTEURS = auto()
    INTERVENTIONS = auto()
    CITOYENS = auto()
    VEHICULES = auto()
    MESURES = auto()
    ZONES = auto()
    TRAJETS = auto()

    # Mots génériques utiles pour l'ambiguïté
    DATA_GENERIC = auto()
    PROBLEME = auto()
    DERNIER = auto()
    CRITIQUE = auto()
    MEILLEUR = auto()

    # Colonnes / attributs
    STATUT = auto()
    NOM = auto()
    SCORE = auto()
    POLLUTION = auto()
    CO2 = auto()
    TAUX_ERREUR = auto()
    DATE = auto()
    ZONE = auto()
    VALEUR = auto()
    TYPE = auto()

    # Comparateurs
    GT = auto()
    LT = auto()
    GTE = auto()
    LTE = auto()
    EQ = auto()

    # Valeurs
    NUMBER = auto()
    STRING = auto()

    # Filtres / modificateurs
    WHERE_KW = auto()
    TOP_KW = auto()
    ORDER_KW = auto()
    DESC_KW = auto()
    ASC_KW = auto()
    LIMIT_KW = auto()

    # Agrégations
    AVG_KW = auto()
    MAX_KW = auto()
    MIN_KW = auto()
    SUM_KW = auto()

    # Statuts
    HORS_SERVICE = auto()
    ACTIF = auto()
    INACTIF = auto()
    SIGNALE = auto()
    EN_MAINTENANCE = auto()
    EN_COURS = auto()
    TERMINE = auto()
    EN_PANNE = auto()
    EN_ROUTE = auto()
    STATIONNE = auto()
    ARRIVE = auto()

    # Logique
    AND = auto()
    OR = auto()
    NOT = auto()

    EOF = auto()
    UNKNOWN = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    position: int

    def __repr__(self):
        return f"Token({self.type.name}, '{self.value}', pos={self.position})"


# IMPORTANT : les expressions les plus spécifiques doivent être avant les plus générales.
KEYWORDS = {
    # Actions
    r"\b(affiche|afficher|montre|montrer|donne|donner|liste|lister|voir)\b": TokenType.SHOW,
    r"\b(combien|compte|compter|nombre)\b": TokenType.COUNT,
    r"\b(trouve|trouver|cherche|chercher|recherche)\b": TokenType.FIND,
    r"\b(récupère|recupere|récupérer|recuperer|obtiens|obtenir|retourne|retourner)\b": TokenType.GET,

    # Entités
    r"\b(capteurs?|sensors?)\b": TokenType.CAPTEURS,
    r"\b(interventions?)\b": TokenType.INTERVENTIONS,
    r"\b(citoyens?|citoyennes?|habitants?)\b": TokenType.CITOYENS,
    r"\b(véhicules?|vehicules?|voitures?)\b": TokenType.VEHICULES,
    r"\b(mesures?|readings?)\b": TokenType.MESURES,
    r"\b(zones?|secteurs?)\b": TokenType.ZONES,
    r"\b(trajets?|parcours?|routes?)\b": TokenType.TRAJETS,

    # Génériques / ambiguïté
    r"\b(données?|donnees?|data|tout|tous|toutes|global|général|general)\b": TokenType.DATA_GENERIC,
    r"\b(problèmes?|problemes?|anomalies?|alertes?|incidents?)\b": TokenType.PROBLEME,
    r"\b(dernier|derniers|dernière|dernières|recent|recents|récent|récents)\b": TokenType.DERNIER,
    r"\b(critique|critiques|urgent|urgents)\b": TokenType.CRITIQUE,
    r"\b(meilleur|meilleure|optimale?|économique|economique)\b": TokenType.MEILLEUR,

    # Colonnes
    r"\b(statut|état|etat|status)\b": TokenType.STATUT,
    r"\b(nom|noms?|name)\b": TokenType.NOM,
    r"\b(score|scores?|score écologique|score ecologique)\b": TokenType.SCORE,
    r"\b(pollution|polluées?|polluees?|polluants?|qualité de l'air|qualite de l'air|air)\b": TokenType.POLLUTION,
    r"\b(co2|carbone|émissions?|emissions?)\b": TokenType.CO2,
    r"\b(taux[_ ]d['’]erreur|taux erreur|erreurs?)\b": TokenType.TAUX_ERREUR,
    r"\b(date|dates?|jour|journée|journee)\b": TokenType.DATE,
    r"\b(zone|secteur)\b": TokenType.ZONE,
    r"\b(valeur|niveau|mesure)\b": TokenType.VALEUR,
    r"\b(type|genre|catégorie|categorie)\b": TokenType.TYPE,

    # Comparateurs : mettre >= avant >
    r"\b(supérieur ou égal|superieur ou egal|au moins|minimum de)\b": TokenType.GTE,
    r"\b(inférieur ou égal|inferieur ou egal|au plus|maximum de)\b": TokenType.LTE,
    r"\b(supérieur|superieur|plus grand|greater|au-dessus|dépasse|depasse|>)\b": TokenType.GT,
    r"\b(inférieur|inferieur|plus petit|less|en-dessous|<)\b": TokenType.LT,
    r"\b(égal|egal|est|vaut|équivaut|equivaut|=)\b": TokenType.EQ,

    # Statuts
    r"\b(hors[_ -]?service|hs|défaillants?|defaillants?)\b": TokenType.HORS_SERVICE,
    r"\b(en[_ -]?maintenance|maintenance)\b": TokenType.EN_MAINTENANCE,
    r"\b(signalés?|signales?|signalé|signale)\b": TokenType.SIGNALE,
    r"\b(actifs?|actives?|en fonctionnement|opérationnels?|operationnels?)\b": TokenType.ACTIF,
    r"\b(inactifs?|désactivés?|desactives?|éteints?|eteints?)\b": TokenType.INACTIF,
    r"\b(en[_ -]?cours|encours|pendants?)\b": TokenType.EN_COURS,
    r"\b(terminés?|terminees?|terminées?|termine|terminé|fini[se]?s?|achevés?|achevees?)\b": TokenType.TERMINE,
    r"\b(en[_ -]?panne|tombés?[_ -]?en[_ -]?panne|pannes?)\b": TokenType.EN_PANNE,
    r"\b(en[_ -]?route)\b": TokenType.EN_ROUTE,
    r"\b(stationnés?|stationnes?|stationné|stationne)\b": TokenType.STATIONNE,
    r"\b(arrivés?|arrivees?|arrivé|arrive)\b": TokenType.ARRIVE,

    # Modificateurs
    r"\b(qui|où|ou|avec|ayant|dont|lequel|lesquels|lesquelles)\b": TokenType.WHERE_KW,
    r"\b(les?\s+\d+\s+plus|top\s+\d+|premiers?\s+\d+)\b": TokenType.TOP_KW,
    r"\b(ordonné|ordonne|classé|classe|trié|trie|rangé|range)\b": TokenType.ORDER_KW,
    r"\b(décroissant|decroissant|descendant|desc|plus grand d['’]?abord)\b": TokenType.DESC_KW,
    r"\b(croissant|ascendant|asc|plus petit d['’]?abord)\b": TokenType.ASC_KW,
    r"\b(limite|limiter|seulement|uniquement)\b": TokenType.LIMIT_KW,

    # Agrégations
    r"\b(moyenne?|moyen|avg)\b": TokenType.AVG_KW,
    r"\b(maximum|max|le plus élevé|le plus eleve|plus élevé|plus eleve)\b": TokenType.MAX_KW,
    r"\b(minimum|min|le moins élevé|le moins eleve|plus petit)\b": TokenType.MIN_KW,
    r"\b(total|somme|sum)\b": TokenType.SUM_KW,

    # Logique
    r"\b(et|and)\b": TokenType.AND,
    r"\b(ou|or)\b": TokenType.OR,
    r"\b(pas|non|not|sans)\b": TokenType.NOT,
}


class Lexer:
    def __init__(self, text: str):
        self.text = (text or "").lower().strip()
        self.tokens: List[Token] = []
        self.errors: List[str] = []

    def tokenize(self) -> List[Token]:
        text = self.text
        self.tokens = []
        matched_ranges = []

        # Nombres
        for m in re.finditer(r"\b\d+(\.\d+)?\b", text):
            self.tokens.append(Token(TokenType.NUMBER, m.group(), m.start()))
            matched_ranges.append((m.start(), m.end()))

        # Chaînes entre guillemets
        for m in re.finditer(r"'([^']+)'|\"([^\"]+)\"", text):
            val = m.group(1) or m.group(2)
            self.tokens.append(Token(TokenType.STRING, val, m.start()))
            matched_ranges.append((m.start(), m.end()))

        # Opérateurs symboliques
        for m in re.finditer(r">=|<=|>|<|=", text):
            if not self._overlaps(m.start(), m.end(), matched_ranges):
                op_map = {
                    ">": TokenType.GT,
                    "<": TokenType.LT,
                    ">=": TokenType.GTE,
                    "<=": TokenType.LTE,
                    "=": TokenType.EQ,
                }
                self.tokens.append(Token(op_map[m.group()], m.group(), m.start()))
                matched_ranges.append((m.start(), m.end()))

        # Mots-clés
        for pattern, ttype in KEYWORDS.items():
            for m in re.finditer(pattern, text, re.IGNORECASE):
                if not self._overlaps(m.start(), m.end(), matched_ranges):
                    self.tokens.append(Token(ttype, m.group(), m.start()))
                    matched_ranges.append((m.start(), m.end()))

        # Identifiants / Mots inconnus (bare strings)
        stop_words = {"le", "la", "les", "l", "d", "un", "une", "de", "des", "du", "à", "a", "au", "aux", "pour", "dans", "sur", "sous", "par", "et", "ou", "qui", "que", "quoi", "dont", "où"}
        for m in re.finditer(r"\b[a-zA-ZÀ-ÿ_][a-zA-ZÀ-ÿ0-9_-]*\b", text):
            if not self._overlaps(m.start(), m.end(), matched_ranges):
                word = m.group().lower()
                if word not in stop_words:
                    self.tokens.append(Token(TokenType.STRING, m.group(), m.start()))
                matched_ranges.append((m.start(), m.end()))

        self._extract_top_numbers()
        self.tokens.sort(key=lambda t: t.position)
        self.tokens.append(Token(TokenType.EOF, "", len(text)))
        return self.tokens

    @staticmethod
    def _overlaps(start: int, end: int, ranges: List[tuple]) -> bool:
        return any(start < e and end > s for s, e in ranges)

    def _extract_top_numbers(self):
        for tok in list(self.tokens):
            if tok.type == TokenType.TOP_KW:
                m = re.search(r"\d+", tok.value)
                if not m:
                    continue
                pos = tok.position + m.start()
                if not any(t.type == TokenType.NUMBER and t.position == pos for t in self.tokens):
                    self.tokens.append(Token(TokenType.NUMBER, m.group(), pos))

    def get_token_stream(self) -> List[Token]:
        return [t for t in self.tokens if t.type != TokenType.EOF]

    def print_tokens(self):
        print(f"\nTexte : {self.text!r}")
        for tok in self.tokens:
            print(f"  {tok}")


if __name__ == "__main__":
    tests = [
        "Affiche les 5 zones les plus polluées",
        "Combien de capteurs sont hors service ?",
        "Quels citoyens ont un score écologique > 80 ?",
        "Donne-moi le trajet le plus économique en CO2",
        "Montre les interventions en cours",
        "Trouve les capteurs actifs avec un taux d'erreur supérieur à 10",
        "Affiche les actifs",
    ]

    for t in tests:
        lex = Lexer(t)
        lex.tokenize()
        lex.print_tokens()
