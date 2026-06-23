AUDIENCE ENRICHMENT
===================

.. image:: https://img.shields.io/badge/python-3.9%2B-blue
.. image:: https://img.shields.io/badge/version-0.1.0-green

**audience_enrichment** is a Python package for enriching event registrant
lists by cross-referencing multiple data sources: LinkedIn connection
exports, congress attendee lists, and Livestorm / Teams registration CSVs.

.. note::
   Developed by `Detralytics <https://detralytics.eu>`_ as part of its
   Innovation Lab tooling for audience intelligence.

----

Overview
--------

The package exposes a simple four-step pipeline:

.. code-block:: text

   ① Load        ② Build contacts     ③ Enrich          ④ Filter
   ─────────     ────────────────     ──────────────     ──────────────
   LinkedIn  ─┐                      fuzzy_match    →   filter by
   Congress  ─┼─► build_contacts ──► enrich_audience    position &
   Livestorm ─┘                      match_stats        company


Quick start
-----------

.. code-block:: python

   from audience_enrichment import loaders, enrichment
   from audience_enrichment.classifiers import classify_position, classify_company

   # ① Load raw sources
   connections  = loaders.load_linkedin_connections("./data")
   congress     = loaders.load_congress_list("./data/Participants congrès 2026.xlsx")
   registrants  = loaders.load_registrants("./data/livestorm-registrants-*.csv")

   # ② Merge into a single contact reference table
   contacts = loaders.build_contacts(connections, congress)

   # ③ Enrich registrants with LinkedIn / congress metadata
   audience = enrichment.enrich_audience(
       registrants, contacts,
       classify_position_fn=classify_position,
       classify_company_fn=classify_company,
   )

   # ④ Report coverage and filter decision-makers
   stats = enrichment.match_stats(registrants, audience)
   print(f"Match rate: {stats['pct_matched']}%")

   decision_makers = enrichment.filter_audience(
       audience,
       positions=["Directeur", "Manager"],
       companies=["Assurance", "Réassurance"],
   )

----

Installation
------------

.. code-block:: bash

   # Development (editable install + dev dependencies)
   uv sync --all-groups
   uv pip install -e .

   # Dependencies installed automatically
   # pandas, numpy, openpyxl, rapidfuzz

----

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/loaders
   api/enrichment
   api/classifiers

.. toctree::
   :maxdepth: 1
   :caption: Development

   changelog

----

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
