"""
SEMANTIC - Analyse sémantique
Valide la cohérence de l'AST avant la génération SQL.
"""

from dataclasses import dataclass
from typing import List, Optional
from nl_parser import QueryNode


SCHEMA = {
    "capteurs": {
        "id": "int",
        "type": "str",
        "zone": "str",
        "statut": "enum:ACTIF,INACTIF,SIGNALE,EN_MAINTENANCE,HORS_SERVICE",
        "date_installation": "date",
    },
    "interventions": {
        "id": "int",
        "capteur_id": "int",
        "technicien1_id": "int",
        "technicien2_id": "int",
        "statut": "enum:DEMANDE,TECH1_ASSIGNE,TECH2_VALIDE,IA_VALIDE,TERMINE,EN_COURS",
        "date": "date",
    },
    "citoyens": {
        "id": "int",
        "nom": "str",
        "score_ecolo": "float",
        "adresse": "str",
    },
    "vehicules": {
        "id": "int",
        "type": "str",
        "trajet_id": "int",
        "statut": "enum:STATIONNE,EN_ROUTE,EN_PANNE,ARRIVE",
    },
    "mesures": {
        "id": "int",
        "capteur_id": "int",
        "type_mesure": "str",
        "valeur": "float",
        "date": "date",
    },
    # Pseudo-entité utilisée par le compilateur pour SELECT DISTINCT zone.
    "zones": {
        "zone": "str",
    },
    # Table prévue par l'énoncé pour le trajet le plus économique en CO2.
    # Si ta base n'a pas encore cette table, ajoute-la ou adapte la route.
    "trajets": {
        "trajet_id": "int",
        "economie_co2": "float",
        "distance": "float",
        "duree": "float",
    },
}

ALLOWED_OPS = {
    "int": ["=", ">", "<", ">=", "<="],
    "float": ["=", ">", "<", ">=", "<="],
    "str": ["=", "LIKE"],
    "date": ["=", ">", "<", ">=", "<="],
    "enum": ["="],
}


@dataclass
class SemanticResult:
    is_valid: bool
    warnings: List[str]
    errors: List[str]
    corrected_node: Optional[QueryNode]


class SemanticAnalyzer:
    def __init__(self, node: QueryNode):
        self.node = node
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def analyze(self) -> SemanticResult:
        # Les templates SQL directs sont déjà validés par le compilateur.
        if getattr(self.node, "raw_sql", None):
            return SemanticResult(True, self.warnings, self.errors, self.node)

        self._check_entity()
        self._check_columns()
        self._check_conditions()
        self._check_order_by()
        self._check_limit()
        self._check_aggregate()

        return SemanticResult(
            is_valid=len(self.errors) == 0,
            warnings=self.warnings,
            errors=self.errors,
            corrected_node=self.node if len(self.errors) == 0 else None,
        )

    def _table_schema(self):
        return SCHEMA.get(self.node.entity, {})

    def _check_entity(self):
        if self.node.entity not in SCHEMA:
            self.errors.append(
                f"Table '{self.node.entity}' inconnue. "
                f"Tables disponibles : {', '.join(SCHEMA.keys())}"
            )

    def _check_columns(self):
        schema = self._table_schema()
        if not schema:
            return

        valid_cols = set(schema.keys()) | {"*"}

        clean_cols = []
        for col in self.node.columns:
            if col in valid_cols:
                clean_cols.append(col)
            else:
                self.warnings.append(
                    f"Colonne '{col}' inconnue dans '{self.node.entity}'. Colonne ignorée."
                )

        if not clean_cols:
            clean_cols = ["*"]

        self.node.columns = clean_cols

    def _check_conditions(self):
        schema = self._table_schema()
        if not schema:
            return

        valid_conditions = []

        for cond in self.node.conditions:
            col = cond.column
            op = cond.operator
            val = cond.value

            if col not in schema:
                self.warnings.append(
                    f"Colonne de condition '{col}' inconnue dans '{self.node.entity}'. Condition ignorée."
                )
                continue

            col_type = schema[col].split(":")[0]
            allowed = ALLOWED_OPS.get(col_type, ["="])

            if op not in allowed:
                self.warnings.append(
                    f"Opérateur '{op}' invalide pour '{col}'. Remplacement par '='."
                )
                cond.operator = "="

            if col_type == "enum":
                enum_vals = schema[col].split(":")[1].split(",")
                val_norm = str(val).upper()
                if val_norm not in enum_vals:
                    self.warnings.append(
                        f"Valeur '{val}' inhabituelle pour '{col}'. Valeurs conseillées : {enum_vals}."
                    )
                cond.value = val_norm

            if col_type in ("int", "float"):
                try:
                    float(val)
                except (ValueError, TypeError):
                    self.errors.append(
                        f"Valeur '{val}' devrait être numérique pour la colonne '{col}'."
                    )
                    continue

            valid_conditions.append(cond)

        self.node.conditions = valid_conditions

    def _check_order_by(self):
        if not self.node.order_by:
            return

        schema = self._table_schema()
        if self.node.order_by not in schema:
            self.warnings.append(
                f"Colonne ORDER BY '{self.node.order_by}' inconnue dans '{self.node.entity}'. ORDER BY retiré."
            )
            self.node.order_by = None

    def _check_limit(self):
        if self.node.limit is None:
            return

        if self.node.limit <= 0:
            self.warnings.append(f"LIMIT {self.node.limit} invalide. LIMIT retiré.")
            self.node.limit = None
        elif self.node.limit > 10000:
            self.warnings.append(f"LIMIT {self.node.limit} très élevé. Attention aux performances.")

    def _check_aggregate(self):
        if not self.node.aggregate or not self.node.agg_column:
            return

        schema = self._table_schema()
        if self.node.agg_column != "*" and self.node.agg_column not in schema:
            self.warnings.append(
                f"Colonne d'agrégation '{self.node.agg_column}' inconnue. Utilisation de '*' à la place."
            )
            self.node.agg_column = "*"


if __name__ == "__main__":
    from lexer import Lexer
    from nl_parser import Parser

    for q in [
        "Combien de capteurs sont hors service ?",
        "Quels citoyens ont un score écologique > 80 ?",
    ]:
        ast = Parser(Lexer(q).tokenize()).parse()
        res = SemanticAnalyzer(ast).analyze()
        print(q, res)
