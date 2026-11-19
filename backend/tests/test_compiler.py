"""
TEST_COMPILER - Suite de tests pour le compilateur NL -> SQL
Smart City Neo-Sousse 2030
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'compilateur'))

from compiler import NLCompiler


TEST_CASES = [
    (
        "TOP 5 zones polluées",
        "Affiche les 5 zones les plus polluées",
        ["FROM mesures m", "JOIN capteurs c", "GROUP BY c.zone", "LIMIT 5"],
    ),
    (
        "Comptage capteurs hors service",
        "Combien de capteurs sont hors service ?",
        ["COUNT(*)", "FROM capteurs", "HORS_SERVICE"],
    ),
    (
        "Citoyens score > 80",
        "Quels citoyens ont un score écologique > 80 ?",
        ["FROM citoyens", "score_ecolo > 80"],
    ),
    (
        "Trajet économique CO2",
        "Donne-moi le trajet le plus économique en CO2",
        ["FROM trajets", "economie_co2", "LIMIT 1"],
    ),
    (
        "Interventions en cours",
        "Montre les interventions en cours",
        ["FROM interventions", "EN_COURS"],
    ),
    (
        "Capteurs taux erreur",
        "Trouve les capteurs actifs avec un taux d'erreur supérieur à 10",
        ["JOIN mesures m", "taux_erreur", "m.valeur > 10"],
    ),
    (
        "Véhicules en panne",
        "Liste les véhicules en panne",
        ["FROM vehicules", "EN_PANNE"],
    ),
    (
        "Interventions terminées",
        "Affiche les interventions terminées",
        ["FROM interventions", "TERMINE"],
    ),
    (
        "Liste citoyens",
        "Liste tous les citoyens",
        ["FROM citoyens"],
    ),
    (
        "Dernières mesures",
        "Donne-moi les 10 dernières mesures",
        ["FROM mesures", "ORDER BY date DESC", "LIMIT 10"],
    ),
    (
        "Capteurs inactifs",
        "Quels capteurs sont inactifs ?",
        ["FROM capteurs", "INACTIF"],
    ),
    (
        "Mesures zone",
        "Montre les mesures de la zone nord",
        ["JOIN capteurs c", "LOWER(c.zone)"],
    ),
]

ERROR_CASES = [
    ("Entité inconnue", "Affiche les ponts détruits"),
    ("Requête vide", ""),
]

AMBIGUOUS_CASES = [
    "Donne les données",
    "Montre tout",
    "Quels sont les problèmes ?",
    "Affiche les actifs",
    "Combien sont en panne ?",
    "Donne-moi les derniers",
    "Affiche la zone la plus critique",
    "Donne-moi le meilleur trajet",
]


class TestRunner:
    def __init__(self):
        self.compiler = NLCompiler(debug=False)
        self.passed = 0
        self.failed = 0

    def run_all(self):
        print("\n" + "=" * 70)
        print("TESTS COMPILATEUR NL -> SQL - Smart City Neo-Sousse 2030")
        print("=" * 70)

        self._run_success_tests()
        self._run_error_tests()
        self._run_ambiguous_tests()
        self._summary()

    def _run_success_tests(self):
        print("\nTests SQL attendus")
        print("-" * 70)

        for i, (desc, query, fragments) in enumerate(TEST_CASES, 1):
            result = self.compiler.compile(query)
            sql = result.sql or ""
            ok = result.success and all(f.lower() in sql.lower() for f in fragments)

            if ok:
                self.passed += 1
                status = "OK"
            else:
                self.failed += 1
                status = "FAIL"

            print(f"\n[{i:02d}] {status} - {desc}")
            print(f"NL  : {query}")
            print(f"SQL : {' '.join(sql.split()) if sql else '---'}")
            if not ok:
                print(f"Attendu : {fragments}")
                print(f"Erreurs : {result.errors}")
            if result.warnings:
                print(f"Warnings : {result.warnings}")

    def _run_error_tests(self):
        print("\nTests erreurs")
        print("-" * 70)

        for i, (desc, query) in enumerate(ERROR_CASES, 1):
            result = self.compiler.compile(query)
            ok = not result.success and not result.ambiguity

            if ok:
                self.passed += 1
                status = "OK"
            else:
                self.failed += 1
                status = "FAIL"

            print(f"\n[{i:02d}] {status} - {desc}")
            print(f"NL : {query!r}")
            print(f"Erreurs : {result.errors}")

    def _run_ambiguous_tests(self):
        print("\nTests ambiguïté")
        print("-" * 70)

        for i, query in enumerate(AMBIGUOUS_CASES, 1):
            result = self.compiler.compile(query)
            ok = result.ambiguity and not result.success and len(result.options) >= 2

            if ok:
                self.passed += 1
                status = "OK"
            else:
                self.failed += 1
                status = "FAIL"

            print(f"\n[{i:02d}] {status}")
            print(f"NL : {query}")
            print(f"Clarification : {result.clarification}")
            for opt in result.options:
                print(f"  - {opt['label']}")

    def _summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print(f"Résultat : {self.passed}/{total} tests réussis")
        print("=" * 70)


def test_lexer():
    from lexer import Lexer, TokenType

    print("\n[Unit] Lexer")
    tests = [
        ("affiche les 5 zones", [TokenType.SHOW, TokenType.NUMBER, TokenType.ZONES]),
        ("combien de capteurs", [TokenType.COUNT, TokenType.CAPTEURS]),
        ("véhicules en panne", [TokenType.VEHICULES, TokenType.EN_PANNE]),
    ]

    for text, expected in tests:
        tokens = Lexer(text).tokenize()
        actual = [t.type for t in tokens]
        ok = all(e in actual for e in expected)
        print(f"{'OK' if ok else 'FAIL'} - {text}")


def test_parser():
    from lexer import Lexer
    from nl_parser import Parser

    print("\n[Unit] Parser")
    tests = [
        ("affiche les capteurs", "capteurs", "SELECT"),
        ("combien de citoyens", "citoyens", "COUNT"),
        ("liste les véhicules en panne", "vehicules", "SELECT"),
    ]

    for text, expected_entity, expected_action in tests:
        ast = Parser(Lexer(text).tokenize()).parse()
        ok = ast.entity == expected_entity and ast.action == expected_action
        print(f"{'OK' if ok else 'FAIL'} - {text} -> {ast}")


if __name__ == "__main__":
    test_lexer()
    test_parser()
    TestRunner().run_all()
