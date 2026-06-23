"""
Tests du module loaders.
Couvre : load_linkedin_connections, load_congress_list,
         load_registrants, build_contacts.
"""
import glob
import os

import pandas as pd
import pytest

from audience_enrichment import loaders


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def write_linkedin_csv(tmp_path, rows, filename="Connections.csv"):
    """Écrit un CSV LinkedIn minimal dans tmp_path."""
    df = pd.DataFrame(rows)
    path = tmp_path / filename
    df.to_csv(path, index=False)
    return str(tmp_path)


def write_congress_xlsx(tmp_path, rows, filename="congres.xlsx"):
    """Écrit un Excel congrès minimal dans tmp_path."""
    df = pd.DataFrame(rows)
    path = tmp_path / filename
    df.to_excel(path, sheet_name="Résumé", index=False)
    return str(path)


def write_registrants_csv(tmp_path, rows, filename="livestorm-registrants.csv"):
    df = pd.DataFrame(rows)
    path = tmp_path / filename
    df.to_csv(path, index=False)
    return str(path)


# ─────────────────────────────────────────────────────────────
# load_linkedin_connections
# ─────────────────────────────────────────────────────────────

class TestLoadLinkedinConnections:
    def test_nominal(self, tmp_path):
        write_linkedin_csv(tmp_path, [
            {"First Name": "Jean", "Last Name": "Dupont",
             "Email Address": "j@axa.fr", "Company": "AXA", "Position": "DT"},
        ])
        df = loaders.load_linkedin_connections(str(tmp_path))
        assert "Name" in df.columns
        assert df["Name"].iloc[0] == "DUPONT, Jean"

    def test_name_format(self, tmp_path):
        """Le format doit être MAJUSCULE, Prénom."""
        write_linkedin_csv(tmp_path, [
            {"First Name": "alice", "Last Name": "martin",
             "Email Address": "", "Company": "", "Position": ""},
        ])
        df = loaders.load_linkedin_connections(str(tmp_path))
        assert df["Name"].iloc[0] == "MARTIN, alice"

    def test_multi_files_concatenated(self, tmp_path):
        """Deux fichiers Connections*.csv doivent être concaténés."""
        for i, (fn, ln) in enumerate([("Anne", "DURAND"), ("Bob", "PETIT")]):
            write_linkedin_csv(
                tmp_path,
                [{"First Name": fn, "Last Name": ln, "Email Address": "",
                  "Company": "", "Position": ""}],
                filename=f"Connections_{i}.csv",
            )
        df = loaders.load_linkedin_connections(str(tmp_path))
        assert len(df) == 2

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            loaders.load_linkedin_connections(str(tmp_path / "inexistant"))

    def test_missing_columns_raises(self, tmp_path):
        (tmp_path / "Connections.csv").write_text("Col1,Col2\na,b\n")
        with pytest.raises(ValueError, match="missing required columns"):
            loaders.load_linkedin_connections(str(tmp_path))

    def test_connected_on_column_dropped(self, tmp_path):
        write_linkedin_csv(tmp_path, [
            {"First Name": "Jean", "Last Name": "Dupont",
             "Email Address": "", "Company": "", "Position": "",
             "Connected On": "01 Jan 2024"},
        ])
        df = loaders.load_linkedin_connections(str(tmp_path))
        assert "Connected On" not in df.columns

    def test_no_duplicates(self, tmp_path):
        rows = [{"First Name": "Jean", "Last Name": "Dupont",
                 "Email Address": "j@a.fr", "Company": "X", "Position": "Y"}] * 3
        write_linkedin_csv(tmp_path, rows)
        df = loaders.load_linkedin_connections(str(tmp_path))
        assert len(df) == 1


class TestLoadCongressList:
    def test_nominal(self, tmp_path):
        path = write_congress_xlsx(tmp_path, [
            {"Name": "DURAND, Alice", "Job": "Actuaire", "Compagnie": "Allianz"},
        ])
        df = loaders.load_congress_list(path)
        assert list(df.columns) == ["Name", "Position", "Company"]
        assert df["Position"].iloc[0] == "Actuaire"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            loaders.load_congress_list(str(tmp_path / "nope.xlsx"))

    def test_missing_columns_raises(self, tmp_path):
        df = pd.DataFrame({"Name": ["X"], "WrongCol": ["Y"]})
        path = tmp_path / "bad.xlsx"
        df.to_excel(path, sheet_name="Résumé", index=False)
        with pytest.raises(KeyError, match="Missing columns"):
            loaders.load_congress_list(str(path))

    def test_position_stripped(self, tmp_path):
        path = write_congress_xlsx(tmp_path, [
            {"Name": "X", "Job": "  Actuaire  ", "Compagnie": "Y"},
        ])
        df = loaders.load_congress_list(path)
        assert df["Position"].iloc[0] == "Actuaire"


class TestLoadRegistrants:
    def test_nominal(self, tmp_path):
        path = write_registrants_csv(tmp_path, [
            {"Nom": "DUPONT", "Prénom": "Jean", "Email": "j@a.fr",
             "Company": "AXA", "Job title": "DT"},
        ])
        df = loaders.load_registrants(path)
        assert "Name" in df.columns
        assert df["Name"].iloc[0] == "DUPONT, Jean"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            loaders.load_registrants(str(tmp_path / "nope.csv"))

    def test_missing_columns_raises(self, tmp_path):
        path = tmp_path / "bad.csv"
        path.write_text("Col1,Col2\na,b\n")
        with pytest.raises(KeyError, match="Missing columns"):
            loaders.load_registrants(str(path))


class TestBuildContacts:
    def test_nominal(self, sample_connections, sample_congress):
        # Simuler les DataFrames normalisés
        linkedin = sample_connections.copy()
        linkedin["Name"] = (
            linkedin["Last Name"].str.upper() + ", " + linkedin["First Name"]
        )
        congress = sample_congress.rename(
            columns={"Job": "Position", "Compagnie": "Company"}
        )
        contacts = loaders.build_contacts(linkedin, congress)
        assert len(contacts) == len(linkedin) + len(congress)
        assert "Name" in contacts.columns

    def test_no_sources_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            loaders.build_contacts()

    def test_missing_name_column_raises(self):
        df = pd.DataFrame({"Col": [1, 2]})
        with pytest.raises(ValueError, match="'Name' column"):
            loaders.build_contacts(df)

    def test_single_source(self, sample_connections):
        linkedin = sample_connections.copy()
        linkedin["Name"] = (
            linkedin["Last Name"].str.upper() + ", " + linkedin["First Name"]
        )
        result = loaders.build_contacts(linkedin)
        assert len(result) == len(linkedin)
