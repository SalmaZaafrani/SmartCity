"""
PARSER - Analyse syntaxique + Construction de l'AST
Transforme les tokens du lexer en un AST simple.

Remarque :
Les cas métier complexes et les requêtes ambiguës sont gérés dans compiler.py.
Le parser reste générique pour les requêtes simples.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional
from lexer import Lexer, Token, TokenType


@dataclass
class ASTNode:
    node_type: str


@dataclass
class ConditionNode(ASTNode):
    column: str
    operator: str
    value: Any

    def __repr__(self):
        return f"Condition({self.column} {self.operator} {self.value!r})"


@dataclass
class QueryNode(ASTNode):
    action: str
    entity: str
    columns: List[str]
    conditions: List[ConditionNode] = field(default_factory=list)
    order_by: Optional[str] = None
    order_dir: str = "DESC"
    limit: Optional[int] = None
    aggregate: Optional[str] = None
    agg_column: Optional[str] = None

    # Utilisé par compiler.py pour les intentions SQL complexes.
    raw_sql: Optional[str] = None
    intent: Optional[str] = None

    def __repr__(self):
        return (
            f"QueryNode(action={self.action}, entity={self.entity}, cols={self.columns}, "
            f"conds={self.conditions}, order={self.order_by} {self.order_dir}, "
            f"limit={self.limit}, aggregate={self.aggregate}, intent={self.intent})"
        )


ENTITY_TABLE = {
    TokenType.CAPTEURS: "capteurs",
    TokenType.INTERVENTIONS: "interventions",
    TokenType.CITOYENS: "citoyens",
    TokenType.VEHICULES: "vehicules",
    TokenType.MESURES: "mesures",
    TokenType.ZONES: "zones",
    TokenType.TRAJETS: "trajets",
}

ENTITY_DEFAULT_COLS = {
    "capteurs": ["id", "type", "zone", "statut", "date_installation"],
    "interventions": ["id", "capteur_id", "technicien1_id", "technicien2_id", "statut", "date"],
    "citoyens": ["id", "nom", "score_ecolo", "adresse"],
    "vehicules": ["id", "type", "trajet_id", "statut"],
    "mesures": ["id", "capteur_id", "type_mesure", "valeur", "date"],
    "zones": ["zone"],
    "trajets": ["trajet_id"],
}

ATTRIBUTE_COLUMN = {
    TokenType.STATUT: "statut",
    TokenType.NOM: "nom",
    TokenType.SCORE: "score_ecolo",
    TokenType.POLLUTION: "valeur",
    TokenType.CO2: "economie_co2",
    TokenType.TAUX_ERREUR: "taux_erreur",
    TokenType.DATE: "date",
    TokenType.ZONE: "zone",
    TokenType.VALEUR: "valeur",
    TokenType.TYPE: "type",
}

COMPARATOR_MAP = {
    TokenType.GT: ">",
    TokenType.LT: "<",
    TokenType.GTE: ">=",
    TokenType.LTE: "<=",
    TokenType.EQ: "=",
}

STATUS_VALUE = {
    TokenType.HORS_SERVICE: "HORS_SERVICE",
    TokenType.ACTIF: "ACTIF",
    TokenType.INACTIF: "INACTIF",
    TokenType.SIGNALE: "SIGNALE",
    TokenType.EN_MAINTENANCE: "EN_MAINTENANCE",
    TokenType.EN_COURS: "EN_COURS",
    TokenType.TERMINE: "TERMINE",
    TokenType.EN_PANNE: "EN_PANNE",
    TokenType.EN_ROUTE: "EN_ROUTE",
    TokenType.STATIONNE: "STATIONNE",
    TokenType.ARRIVE: "ARRIVE",
}

AGGREGATE_MAP = {
    TokenType.AVG_KW: "AVG",
    TokenType.MAX_KW: "MAX",
    TokenType.MIN_KW: "MIN",
    TokenType.SUM_KW: "SUM",
}


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens or []
        self.pos = 0
        self.errors: List[str] = []

    def current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, "", -1)

    def advance(self) -> Token:
        tok = self.current()
        self.pos += 1
        return tok

    def match(self, *types: TokenType) -> bool:
        return self.current().type in types

    def consume(self, *types: TokenType) -> Optional[Token]:
        if self.match(*types):
            return self.advance()
        return None

    def parse(self) -> QueryNode:
        if not self.tokens or all(t.type == TokenType.EOF for t in self.tokens):
            raise ParseError("Requête vide.")

        action_type = self._parse_action()
        aggregate = self._parse_aggregate()
        entity = self._parse_entity()

        if entity is None:
            entity = self._search_entity_anywhere()

        if entity is None:
            raise ParseError(
                "Entité non reconnue. Entités supportées : "
                "capteurs, interventions, citoyens, véhicules, mesures, zones, trajets."
            )

        columns = list(ENTITY_DEFAULT_COLS.get(entity, ["*"]))
        limit = self._parse_limit()
        conditions = self._parse_conditions(entity)
        order_by, order_dir, extra_limit = self._parse_modifiers(entity)

        if extra_limit and not limit:
            limit = extra_limit

        sql_action = "COUNT" if action_type == TokenType.COUNT else "SELECT"
        agg_column = self._resolve_agg_column(aggregate, entity)

        return QueryNode(
            node_type="Query",
            action=sql_action,
            entity=entity,
            columns=columns,
            conditions=conditions,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            aggregate=aggregate,
            agg_column=agg_column,
        )

    def _parse_action(self) -> TokenType:
        for i, tok in enumerate(self.tokens[:6]):
            if tok.type in (TokenType.SHOW, TokenType.COUNT, TokenType.FIND, TokenType.GET):
                self.pos = max(self.pos, i + 1)
                return tok.type
        return TokenType.SHOW

    def _parse_aggregate(self) -> Optional[str]:
        for tok in self.tokens:
            if tok.type in AGGREGATE_MAP:
                return AGGREGATE_MAP[tok.type]
        return None

    def _parse_entity(self) -> Optional[str]:
        entity_types = tuple(ENTITY_TABLE.keys())
        for i in range(self.pos, min(self.pos + 10, len(self.tokens))):
            tok = self.tokens[i]
            if tok.type in entity_types:
                self.pos = i + 1
                return ENTITY_TABLE[tok.type]
        return None

    def _search_entity_anywhere(self) -> Optional[str]:
        for tok in self.tokens:
            if tok.type in ENTITY_TABLE:
                return ENTITY_TABLE[tok.type]
        return None

    def _parse_limit(self) -> Optional[int]:
        for i, tok in enumerate(self.tokens):
            if tok.type == TokenType.TOP_KW:
                import re
                m = re.search(r"\d+", tok.value)
                if m:
                    return int(m.group())

            if tok.type == TokenType.LIMIT_KW:
                for j in range(i + 1, min(i + 4, len(self.tokens))):
                    if self.tokens[j].type == TokenType.NUMBER:
                        return int(float(self.tokens[j].value))

            # "5 zones", "10 capteurs"
            if tok.type == TokenType.NUMBER:
                for j in range(i + 1, min(i + 4, len(self.tokens))):
                    if self.tokens[j].type in ENTITY_TABLE:
                        return int(float(tok.value))

        return None

    def _parse_conditions(self, entity: str) -> List[ConditionNode]:
        conditions: List[ConditionNode] = []
        toks = [t for t in self.tokens if t.type != TokenType.EOF]

        for i, tok in enumerate(toks):
            # Statut implicite : "capteurs actifs", "véhicules en panne"
            if tok.type in STATUS_VALUE:
                self._add_condition_once(conditions, "statut", "=", STATUS_VALUE[tok.type])
                continue

            # Attribut + opérateur + valeur
            if tok.type in ATTRIBUTE_COLUMN:
                col = ATTRIBUTE_COLUMN[tok.type]
                op = None
                val = None

                for j in range(i + 1, min(i + 5, len(toks))):
                    if toks[j].type in COMPARATOR_MAP:
                        op = COMPARATOR_MAP[toks[j].type]

                        for k in range(j + 1, min(j + 5, len(toks))):
                            if toks[k].type == TokenType.NUMBER:
                                val = self._number_value(toks[k].value)
                                break
                            if toks[k].type == TokenType.STRING:
                                val = toks[k].value
                                break
                            if toks[k].type in STATUS_VALUE:
                                val = STATUS_VALUE[toks[k].type]
                                break
                        break
                    elif toks[j].type in (TokenType.NUMBER, TokenType.STRING) or toks[j].type in STATUS_VALUE:
                        op = "="
                        if toks[j].type == TokenType.NUMBER:
                            val = self._number_value(toks[j].value)
                        elif toks[j].type == TokenType.STRING:
                            val = toks[j].value
                        else:
                            val = STATUS_VALUE[toks[j].type]
                        break

                if op is not None and val is not None:
                    self._add_condition_once(conditions, col, op, val)

        return conditions

    @staticmethod
    def _number_value(value: str):
        return float(value) if "." in value else int(value)

    @staticmethod
    def _add_condition_once(conditions: List[ConditionNode], col: str, op: str, val: Any):
        for c in conditions:
            if c.column == col and c.operator == op and c.value == val:
                return
        conditions.append(ConditionNode("Condition", col, op, val))

    def _parse_modifiers(self, entity: str):
        order_by = None
        order_dir = "DESC"
        limit = None

        for i, tok in enumerate(self.tokens):
            if tok.type == TokenType.ORDER_KW and not order_by:
                order_by = self._default_order_col(entity)

            if tok.type == TokenType.DESC_KW:
                order_dir = "DESC"

            if tok.type == TokenType.ASC_KW:
                order_dir = "ASC"

            if tok.type == TokenType.LIMIT_KW:
                for j in range(i + 1, min(i + 4, len(self.tokens))):
                    if self.tokens[j].type == TokenType.NUMBER:
                        limit = int(float(self.tokens[j].value))
                        break

        if not order_by:
            order_by = self._infer_order_by(entity)

        return order_by, order_dir, limit

    def _default_order_col(self, entity: str) -> str:
        return {
            "citoyens": "score_ecolo",
            "capteurs": "id",
            "interventions": "date",
            "vehicules": "id",
            "mesures": "date",
            "zones": "zone",
            "trajets": "trajet_id",
        }.get(entity, "id")

    def _infer_order_by(self, entity: str) -> Optional[str]:
        token_types = {t.type for t in self.tokens}

        if TokenType.SCORE in token_types:
            return "score_ecolo"
        if TokenType.DATE in token_types or TokenType.DERNIER in token_types:
            return "date"
        if TokenType.CO2 in token_types:
            return "economie_co2"
        if TokenType.POLLUTION in token_types and entity == "mesures":
            return "valeur"
        if TokenType.TAUX_ERREUR in token_types:
            return "taux_erreur"

        return None

    def _resolve_agg_column(self, aggregate: Optional[str], entity: str) -> Optional[str]:
        if not aggregate:
            return None

        return {
            "mesures": "valeur",
            "citoyens": "score_ecolo",
            "capteurs": "id",
            "interventions": "id",
            "vehicules": "id",
            "zones": "zone",
            "trajets": "trajet_id",
        }.get(entity, "*")


if __name__ == "__main__":
    queries = [
        "Affiche les 5 zones les plus polluées",
        "Combien de capteurs sont hors service ?",
        "Quels citoyens ont un score écologique > 80 ?",
        "Montre les interventions en cours",
    ]

    for q in queries:
        print(f"\nRequête : {q!r}")
        tokens = Lexer(q).tokenize()
        print(Parser(tokens).parse())
