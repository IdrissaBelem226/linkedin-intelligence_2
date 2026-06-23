Changelog
=========

v0.1.0 — June 2026
-------------------

Initial release.

**Loaders**

- :func:`~audience_enrichment.loaders.load_linkedin_connections` — multi-file glob, deduplication, ``Connected On`` column removal.
- :func:`~audience_enrichment.loaders.load_congress_list` — Excel reader with column validation and whitespace normalisation.
- :func:`~audience_enrichment.loaders.load_registrants` — Livestorm CSV loader with glob pattern support.
- :func:`~audience_enrichment.loaders.build_contacts` — variadic concat with ``Name`` column validation.

**Enrichment**

- :func:`~audience_enrichment.enrichment.fuzzy_match` — WRatio fuzzy matching via ``rapidfuzz``, configurable ``score_cutoff``.
- :func:`~audience_enrichment.enrichment.enrich_audience` — full pipeline with optional classifiers injection.
- :func:`~audience_enrichment.enrichment.match_stats` — coverage reporting with unmatched name list.
- :func:`~audience_enrichment.enrichment.filter_audience` — combined position + company filtering.

**Classifiers**

- :func:`~audience_enrichment.classifiers.classify_position` — 5-tier priority-ordered regex classifier (Etudiant → Junior).
- :func:`~audience_enrichment.classifiers.classify_company` — 3-pass classifier: exact match, partial match, regex fallback.
