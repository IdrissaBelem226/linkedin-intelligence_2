"""
Tests du module enrichment.
Couvre : fuzzy_match, enrich_audience, match_stats, filter_audience.
"""
import pandas as pd
import pytest

from audience_enrichment import enrichment
from audience_enrichment.classifiers import classify_position, classify_company


# ─────────────────────────────────────────────────────────────
# fuzzy_match
# ─────────────────────────────────────────────────────────────

class TestFuzzyMatch:
    def test_exact_match(self, sample_registrants, sample_contacts):
        result = enrichment.fuzzy_match(sample_registrants, sample_contacts)
        # "DUPONT, Jean" est exact → score 100
        row = result[result["Name registrant"] == "DUPONT, Jean"].iloc[0]
        assert row["Score"] == 100.0
        assert row["Name fuzzy matched"] == "DUPONT, Jean"

    def test_no_match_below_cutoff(self, sample_contacts):
        registrants = pd.DataFrame({"Name": ["ZZZZZZ, Xxxxxxx"]})
        result = enrichment.fuzzy_match(registrants, sample_contacts, score_cutoff=90)
        assert result["Name fuzzy matched"].isna().all()
        assert result["Score"].isna().all()

    def test_output_columns(self, sample_registrants, sample_contacts):
        result = enrichment.fuzzy_match(sample_registrants, sample_contacts)
        assert set(result.columns) == {
            "Name registrant", "Name fuzzy matched", "Score", "Index"
        }

    def test_one_row_per_registrant(self, sample_registrants, sample_contacts):
        result = enrichment.fuzzy_match(sample_registrants, sample_contacts)
        assert len(result) == len(sample_registrants)

    def test_approximate_match(self, sample_contacts):
        """Légère faute de frappe : doit quand même matcher avec cutoff bas."""
        registrants = pd.DataFrame({"Name": ["DUPONT, Jeen"]})   # "Jeen" ≠ "Jean"
        result = enrichment.fuzzy_match(registrants, sample_contacts, score_cutoff=80)
        assert result["Name fuzzy matched"].notna().any()

    def test_custom_cutoff_filters(self, sample_contacts):
        """Score 100 attendu en exact match, cutoff=100 doit passer."""
        registrants = pd.DataFrame({"Name": ["DUPONT, Jean"]})
        result = enrichment.fuzzy_match(registrants, sample_contacts, score_cutoff=100)
        assert result["Name fuzzy matched"].iloc[0] == "DUPONT, Jean"

    def test_high_cutoff_rejects(self, sample_contacts):
        """Coupure à 100 doit rejeter les matchs approximatifs."""
        registrants = pd.DataFrame({"Name": ["DUPONT, Jeen"]})
        result = enrichment.fuzzy_match(registrants, sample_contacts, score_cutoff=100)
        assert result["Name fuzzy matched"].isna().all()


# ─────────────────────────────────────────────────────────────
# enrich_audience
# ─────────────────────────────────────────────────────────────

class TestEnrichAudience:
    def test_base_columns_present(self, sample_registrants, sample_contacts):
        audience = enrichment.enrich_audience(sample_registrants, sample_contacts)
        for col in ["Name", "Name registrant"]:
            assert col in audience.columns

    def test_unmatched_excluded(self, sample_registrants, sample_contacts):
        """INCONNU, Robert ne doit pas apparaître dans le résultat."""
        audience = enrichment.enrich_audience(sample_registrants, sample_contacts)
        assert "INCONNU, Robert" not in audience["Name registrant"].values

    def test_with_classifiers(self, sample_registrants, sample_contacts):
        audience = enrichment.enrich_audience(
            sample_registrants, sample_contacts,
            classify_position_fn=classify_position,
            classify_company_fn=classify_company,
        )
        assert "Category_position" in audience.columns
        assert "Category_company" in audience.columns

    def test_without_classifiers_no_category_columns(self, sample_registrants, sample_contacts):
        audience = enrichment.enrich_audience(sample_registrants, sample_contacts)
        assert "Category_position" not in audience.columns
        assert "Category_company" not in audience.columns

    def test_position_stripped(self, sample_registrants, sample_contacts):
        """Les espaces dans Position doivent être éliminés."""
        sample_contacts_copy = sample_contacts.copy()
        if "Position" in sample_contacts_copy.columns:
            sample_contacts_copy["Position"] = "  Manager  "
            audience = enrichment.enrich_audience(sample_registrants, sample_contacts_copy)
            if "Position" in audience.columns:
                assert not audience["Position"].str.startswith(" ").any()


# ─────────────────────────────────────────────────────────────
# match_stats
# ─────────────────────────────────────────────────────────────

class TestMatchStats:
    def test_keys_present(self, sample_registrants, sample_contacts):
        audience = enrichment.enrich_audience(sample_registrants, sample_contacts)
        stats = enrichment.match_stats(sample_registrants, audience)
        expected_keys = {
            "n_registered", "n_matched", "n_unmatched",
            "pct_matched", "pct_unmatched", "unmatched_names",
        }
        assert expected_keys == set(stats.keys())

    def test_counts_consistent(self, sample_registrants, sample_contacts):
        audience = enrichment.enrich_audience(sample_registrants, sample_contacts)
        stats = enrichment.match_stats(sample_registrants, audience)
        assert stats["n_registered"] == len(sample_registrants)
        assert stats["n_matched"] + stats["n_unmatched"] == stats["n_registered"]

    def test_pct_sums_to_100(self, sample_registrants, sample_contacts):
        audience = enrichment.enrich_audience(sample_registrants, sample_contacts)
        stats = enrichment.match_stats(sample_registrants, audience)
        total = stats["pct_matched"] + stats["pct_unmatched"]
        assert abs(total - 100.0) < 0.01

    def test_unmatched_names_correct(self, sample_registrants, sample_contacts):
        audience = enrichment.enrich_audience(sample_registrants, sample_contacts)
        stats = enrichment.match_stats(sample_registrants, audience)
        assert "INCONNU, Robert" in stats["unmatched_names"]

    def test_empty_registrants(self, sample_contacts):
        empty = pd.DataFrame({"Name": []})
        audience = enrichment.enrich_audience(empty, sample_contacts)
        stats = enrichment.match_stats(empty, audience)
        assert stats["pct_matched"] == 0.0
        assert stats["n_registered"] == 0


# ─────────────────────────────────────────────────────────────
# filter_audience
# ─────────────────────────────────────────────────────────────

class TestFilterAudience:
    @pytest.fixture
    def enriched_audience(self, sample_registrants, sample_contacts):
        return enrichment.enrich_audience(
            sample_registrants, sample_contacts,
            classify_position_fn=classify_position,
            classify_company_fn=classify_company,
        )

    def test_filter_by_position(self, enriched_audience):
        result = enrichment.filter_audience(
            enriched_audience, positions=["Directeur"]
        )
        assert all(result["Category_position"] == "Directeur")

    def test_filter_by_company(self, enriched_audience):
        result = enrichment.filter_audience(
            enriched_audience, companies=["Assurance"]
        )
        assert all(result["Category_company"] == "Assurance")

    def test_filter_combined(self, enriched_audience):
        result = enrichment.filter_audience(
            enriched_audience,
            positions=["Directeur", "Manager"],
            companies=["Assurance", "Cabinet de conseil"],
        )
        assert all(result["Category_position"].isin(["Directeur", "Manager"]))
        assert all(result["Category_company"].isin(["Assurance", "Cabinet de conseil"]))

    def test_no_filter_returns_all(self, enriched_audience):
        result = enrichment.filter_audience(enriched_audience)
        assert len(result) == len(enriched_audience)

    def test_missing_category_column_raises(self, sample_registrants, sample_contacts):
        """Sans classifier, filter_audience doit lever KeyError."""
        audience = enrichment.enrich_audience(sample_registrants, sample_contacts)
        with pytest.raises(KeyError, match="Category_position"):
            enrichment.filter_audience(audience, positions=["Directeur"])

    def test_missing_company_category_raises(self, sample_registrants, sample_contacts):
        """Sans classify_company_fn, filter sur companies doit lever KeyError."""
        audience = enrichment.enrich_audience(
            sample_registrants, sample_contacts,
            classify_position_fn=classify_position,
            # classify_company_fn absent → Category_company manquante
        )
        with pytest.raises(KeyError, match="Category_company"):
            enrichment.filter_audience(audience, companies=["Assurance"])

    def test_empty_result(self, enriched_audience):
        """Catégorie inexistante → DataFrame vide (pas d'erreur)."""
        result = enrichment.filter_audience(
            enriched_audience, positions=["CatégorieInexistante"]
        )
        assert len(result) == 0
