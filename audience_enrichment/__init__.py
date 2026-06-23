"""
audience_enrichment
===================

Package pour enrichir une liste de participants à un événement
en croisant plusieurs sources de données (LinkedIn, congrès, registrants).

Modules
-------
- loaders   : import et nettoyage de chaque source de données
- enrichment: fusion, fuzzy matching et enrichissement des participants
- classifiers: classification des postes et entreprises (fourni séparément)

Exemple d'utilisation rapide
-----------------------------
>>> from audience_enrichment import loaders, enrichment
>>>
>>> connections  = loaders.load_linkedin_connections("./")
>>> congress     = loaders.load_congress_list("Participants congrès 2026.xlsx")
>>> registrants  = loaders.load_registrants("livestorm-registrants-*.csv")
>>>
>>> contacts     = loaders.build_contacts(connections, congress)
>>> audience     = enrichment.enrich_audience(registrants, contacts)
>>> stats        = enrichment.match_stats(registrants, audience)
"""

from .loaders import (
    load_linkedin_connections,
    load_congress_list,
    load_registrants,
    build_contacts,
)
from .enrichment import (
    fuzzy_match,
    enrich_audience,
    match_stats,
    filter_audience,
)
from .classifiers import (
    classify_position,
    classify_company,
)
__all__ = [
    "load_linkedin_connections",
    "load_congress_list",
    "load_registrants",
    "build_contacts",
    "fuzzy_match",
    "enrich_audience",
    "match_stats",
    "filter_audience",
    "classify_position",
    "classify_company",
]
