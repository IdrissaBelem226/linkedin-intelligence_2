"""
Fixtures partagées entre tous les tests.
"""
import pandas as pd
import pytest


@pytest.fixture
def sample_connections():
    """Export LinkedIn minimal valide."""
    return pd.DataFrame({
        "First Name": ["Jean", "Marie", "Pierre", "Sophie"],
        "Last Name":  ["Dupont", "Martin", "Bernard", "Leclerc"],
        "Email Address": ["j.dupont@axa.fr", "m.martin@detralytics.fr",
                          "p.bernard@scor.com", "s.leclerc@univ-paris.fr"],
        "Company":   ["AXA", "Detralytics", "SCOR", "Université de Paris"],
        "Position":  ["Directeur technique", "Manager actuarial",
                      "Chargé de réassurance", "Professeur"],
        "URL": ["https://linkedin.com/in/jdupont", "https://linkedin.com/in/mmartin",
                "https://linkedin.com/in/pbernard", "https://linkedin.com/in/sleclerc"],
    })


@pytest.fixture
def sample_congress():
    """Liste congrès minimale valide."""
    return pd.DataFrame({
        "Name":      ["DURAND, Alice", "PETIT, Marc"],
        "Job":       ["Actuaire senior", "Stagiaire actuariat"],
        "Compagnie": ["Allianz", "Nexialog"],
    })


@pytest.fixture
def sample_contacts(sample_connections, sample_congress):
    """Table contacts construite (LinkedIn + congrès)."""
    from audience_enrichment import loaders
    linkedin = sample_connections.copy()
    linkedin["Name"] = (
        linkedin["Last Name"].str.upper().str.strip()
        + ", "
        + linkedin["First Name"].str.strip()
    )
    congress = sample_congress.rename(
        columns={"Job": "Position", "Compagnie": "Company"}
    )
    return pd.concat([linkedin, congress], ignore_index=True)


@pytest.fixture
def sample_registrants():
    """Registrants Livestorm — noms identiques ou proches des contacts."""
    return pd.DataFrame({
        "Name": ["DUPONT, Jean", "MARTIN, Marie", "DURAND, Alice",
                 "INCONNU, Robert"],   # ce dernier ne matchera pas
        "Email": ["j@axa.fr", "m@detra.fr", "a@allianz.fr", "r@nowhere.fr"],
    })
