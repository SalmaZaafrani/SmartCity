"""
CODEGEN - Génération SQL depuis l'AST
Transforme un QueryNode validé en requête SQL exécutable.

Les requêtes complexes peuvent arriver avec node.raw_sql.
"""

from typing import Optional
from nl_parser import QueryNode, ConditionNode


class SQLGenerator:
    def __init__(self, node: QueryNode):
        self.node = node

    def generate(self) -> str:
        if getattr(self.node, "raw_sql", None):
            sql = self.node.raw_sql.strip()
            return sql if sql.endswith(";") else sql + ";"

        if self.node.action == "COUNT":
            return self._generate_count()

        return self._generate_select()

    def _generate_select(self) -> str:
        parts = [f"SELECT {self._build_select_clause()}"]

        if self.node.entity == "zones":
            parts.append("FROM (SELECT DISTINCT zone FROM capteurs) zones")
        else:
            parts.append(f"FROM {self.node.entity}")

        where = self._build_where_clause()
        if where:
            parts.append(f"WHERE {where}")

        group_by = self._get_group_by_column()
        if self.node.aggregate and group_by:
            parts.append(f"GROUP BY {group_by}")

        if self.node.order_by:
            parts.append(f"ORDER BY {self._build_order_clause()} {self.node.order_dir}")

        if self.node.limit:
            parts.append(f"LIMIT {self.node.limit}")

        return "\n".join(parts) + ";"

    def _generate_count(self) -> str:
        if self.node.entity == "zones":
            parts = ["SELECT COUNT(DISTINCT zone) AS total", "FROM capteurs"]
        else:
            parts = ["SELECT COUNT(*) AS total", f"FROM {self.node.entity}"]

        where = self._build_where_clause()
        if where:
            parts.append(f"WHERE {where}")

        return "\n".join(parts) + ";"

    def _build_select_clause(self) -> str:
        if self.node.aggregate and self.node.agg_column:
            agg = self.node.aggregate
            col = self.node.agg_column

            if col == "*":
                return f"{agg}(*) AS {agg.lower()}"

            alias = f"{agg.lower()}_{self._clean_alias(col)}"
            agg_expr = f"{agg}({col}) AS {alias}"

            group_col = self._get_group_by_column()
            if group_col:
                return f"{group_col}, {agg_expr}"

            return agg_expr

        if not self.node.columns or self.node.columns == ["*"]:
            return "*"

        if self.node.entity == "zones":
            return "zone"

        return ", ".join(self.node.columns)

    def _build_where_clause(self) -> str:
        if not self.node.conditions:
            return ""

        return " AND ".join(self._format_condition(cond) for cond in self.node.conditions)

    def _format_condition(self, cond: ConditionNode) -> str:
        col = cond.column
        op = cond.operator
        val = cond.value

        # Statuts robustes : accepte les valeurs stockées en majuscules ou minuscules.
        if col == "statut" and isinstance(val, str):
            return f"UPPER({col}) {op} '{self._escape_sql(val.upper())}'"

        if isinstance(val, str):
            return f"{col} {op} '{self._escape_sql(val)}'"

        return f"{col} {op} {val}"

    def _build_order_clause(self) -> str:
        if self.node.aggregate and self.node.agg_column:
            return f"{self.node.aggregate}({self.node.agg_column})"
        return self.node.order_by

    def _get_group_by_column(self) -> Optional[str]:
        if not self.node.aggregate:
            return None

        group_map = {
            "zones": "zone",
            "mesures": None,
            "capteurs": None,
            "citoyens": None,
            "interventions": None,
            "vehicules": None,
            "trajets": None,
        }
        return group_map.get(self.node.entity)

    @staticmethod
    def _escape_sql(value: str) -> str:
        return str(value).replace("'", "''")

    @staticmethod
    def _clean_alias(value: str) -> str:
        return value.replace(".", "_").replace("(", "").replace(")", "").replace("*", "total")

    def to_single_line(self) -> str:
        return " ".join(self.generate().split())


if __name__ == "__main__":
    from lexer import Lexer
    from nl_parser import Parser
    from semantic import SemanticAnalyzer

    queries = [
        "Combien de capteurs sont hors service ?",
        "Quels citoyens ont un score écologique > 80 ?",
        "Montre les interventions en cours",
    ]

    for q in queries:
        print(f"\nNL : {q}")
        ast = Parser(Lexer(q).tokenize()).parse()
        sem = SemanticAnalyzer(ast).analyze()
        if sem.is_valid:
            print(SQLGenerator(sem.corrected_node).generate())
        else:
            print(sem.errors)
