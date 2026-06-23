"""
Tests du module classifiers.
Couvre : classify_position, classify_company — cas nominaux, limites et edge cases.
"""
import pytest
from audience_enrichment.classifiers import classify_position, classify_company


# ─────────────────────────────────────────────────────────────
# classify_position
# ─────────────────────────────────────────────────────────────

class TestClassifyPosition:

    # ── Cas nominaux par catégorie ────────────────────────────
    @pytest.mark.parametrize("title,expected", [
        # Etudiant
        ("Étudiant en actuariat",       "Etudiant"),
        ("Master 2 actuariat",           "Etudiant"),
        ("Student actuary",              "Etudiant"),
        # Stagiaire
        ("Stagiaire actuariat",          "Stagiaire"),
        ("Data science intern",          "Stagiaire"),
        ("Internship at AXA",            "Stagiaire"),
        # Alternant
        ("Alternant actuariat",          "Alternant"),
        ("Contrat pro - pricing",        "Alternant"),
        ("Apprenti data scientist",      "Alternant"),
        # Directeur
        ("Directeur technique",          "Directeur"),
        ("Head of Pricing",              "Directeur"),
        ("CEO",                          "Directeur"),
        ("CTO chez SCOR",               "Directeur"),
        ("Président directeur général",  "Directeur"),
        ("Fondateur de startup",         "Directeur"),
        ("Vice-President Risk",          "Directeur"),
        ("Professeur des universités",   "Directeur"),
        # Manager
        ("Manager actuarial",            "Manager"),
        ("Responsable pricing",          "Manager"),
        ("Senior actuaire",              "Manager"),
        ("Expert sinistres",             "Manager"),
        ("Team Lead data science",       "Manager"),
        # Junior (défaut)
        ("Actuaire non-vie",             "Junior"),
        ("Data analyst",                 "Junior"),
        ("Chargé d'études",              "Junior"),
    ])
    def test_nominal(self, title, expected):
        assert classify_position(title) == expected

    # ── Edge cases ────────────────────────────────────────────
    def test_empty_string(self):
        assert classify_position("") == ""

    def test_whitespace_only(self):
        assert classify_position("   ") == ""

    def test_none_like_empty(self):
        # La fonction attend un str ; tester qu'elle ne plante pas sur falsy
        assert classify_position("") == ""

    def test_case_insensitive(self):
        assert classify_position("DIRECTEUR GENERAL") == "Directeur"
        assert classify_position("manager") == "Manager"

    def test_priority_etudiant_over_junior(self):
        """Un étudiant ne doit pas tomber en Junior malgré l'absence d'autre mot."""
        assert classify_position("Etudiant") == "Etudiant"

    def test_priority_stagiaire_over_manager(self):
        """Un stagiaire senior → Stagiaire (priorité Stagiaire avant Manager)."""
        result = classify_position("Stagiaire senior actuariat")
        # Stagiaire arrive avant Manager dans RULES_POSITIONS
        assert result == "Stagiaire"


# ─────────────────────────────────────────────────────────────
# classify_company
# ─────────────────────────────────────────────────────────────

class TestClassifyCompany:

    # ── Exact matches KNOWN_COMPANIES ────────────────────────
    @pytest.mark.parametrize("company,expected", [
        ("axa",                          "Assurance"),
        ("AXA",                          "Assurance"),
        ("maif",                         "Assurance"),
        ("detralytics",                  "Cabinet de conseil"),
        ("oliver wyman",                 "Cabinet de conseil"),
        ("scor",                         "Réassurance"),
        ("aon",                          "Courtier"),
        ("université libre de bruxelles","Scolaire"),
    ])
    def test_known_exact(self, company, expected):
        assert classify_company(company) == expected

    # ── Regex fallback ────────────────────────────────────────
    @pytest.mark.parametrize("company,expected", [
        ("Groupama Assurances Mutuelles", "Assurance"),
        ("Munich Re International",       "Réassurance"),
        ("Actuarial Consulting Group",    "Cabinet de conseil"),
        ("Université de Bordeaux",        "Scolaire"),
        ("Marsh & McLennan",              "Courtier"),
    ])
    def test_regex_fallback(self, company, expected):
        assert classify_company(company) == expected

    # ── Défaut ────────────────────────────────────────────────
    def test_unknown_company(self):
        assert classify_company("Entreprise XYZ Inconnue") == "Autre"

    # ── Edge cases ────────────────────────────────────────────
    def test_empty_string(self):
        assert classify_company("") == ""

    def test_whitespace_only(self):
        assert classify_company("   ") == ""

    def test_case_insensitive_known(self):
        assert classify_company("AXA EN FRANCE") == "Assurance"

    def test_partial_match_known(self):
        """Correspondance partielle : "allianz france" contient "allianz"."""
        assert classify_company("allianz france") == "Assurance"
