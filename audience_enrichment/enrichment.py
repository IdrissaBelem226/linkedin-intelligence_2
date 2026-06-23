"""
audience_enrichment.enrichment
================================

Fuzzy matching, audience enrichment, coverage statistics, and filtering.

This module is the analytical core of the package.  It provides four
public functions that form a natural pipeline:

.. code-block:: text

   registrants ──┐
                 ├─► fuzzy_match ──► enrich_audience ──► match_stats
   contacts ─────┘                        │
                                          ▼
                                   filter_audience

Typical usage
-------------
>>> from audience_enrichment import loaders, enrichment
>>> from audience_enrichment.classifiers import classify_position, classify_company
>>>
>>> contacts    = loaders.build_contacts(connections, congress)
>>> audience    = enrichment.enrich_audience(
...     registrants, contacts,
...     classify_position_fn=classify_position,
...     classify_company_fn=classify_company,
... )
>>> stats       = enrichment.match_stats(registrants, audience)
>>> decision_makers = enrichment.filter_audience(
...     audience,
...     positions=["Directeur", "Manager"],
...     companies=["Assurance", "Réassurance"],
... )

Fuzzy matching algorithm
------------------------
Name matching relies on :func:`rapidfuzz.process.extractOne` with the
**WRatio** scorer, which combines several string-similarity algorithms
(partial ratio, token sort ratio, token set ratio) and selects the
highest score.  The default ``score_cutoff`` of **90** was chosen to
minimise false positives on French proper names while still tolerating
minor spelling variants and abbreviations.

+-------------------+--------------------------------------------------+
| score_cutoff      | Effect                                           |
+===================+==================================================+
| 100               | Exact matches only                               |
+-------------------+--------------------------------------------------+
| 90 *(default)*    | Good precision/recall trade-off                  |
+-------------------+--------------------------------------------------+
| 80                | Higher recall; more false positives              |
+-------------------+--------------------------------------------------+
| < 70              | Not recommended — too many spurious matches      |
+-------------------+--------------------------------------------------+
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from rapidfuzz.process import extractOne


# ===========================================================================
# Fuzzy matching
# ===========================================================================


def fuzzy_match(
    registrants: pd.DataFrame,
    contacts: pd.DataFrame,
    score_cutoff: float = 90.0,
) -> pd.DataFrame:
    """Match each registrant to the closest contact using fuzzy string matching.

    Uses :func:`rapidfuzz.process.extractOne` (WRatio algorithm) to find,
    among the names in the *contacts* reference table, the best match for
    each registrant name.  Names that score below *score_cutoff* are left
    unmatched (``NaN`` in the result columns).

    Parameters
    ----------
    registrants : pd.DataFrame
        DataFrame of registrants.  Must contain a ``Name`` column formatted
        as ``"LASTNAME, Firstname"`` (produced by
        :func:`~audience_enrichment.loaders.load_registrants`).
    contacts : pd.DataFrame
        Contact reference table (LinkedIn exports + congress list).
        Must contain a ``Name`` column in the same format (produced by
        :func:`~audience_enrichment.loaders.build_contacts`).
    score_cutoff : float, optional
        Minimum similarity score in the range ``[0, 100]`` below which no
        match is retained.  Default is ``90.0``.

    Returns
    -------
    pd.DataFrame
        One row per registrant with the following columns:

        ``Name registrant``
            Name as it appears in the registrant list.
        ``Name fuzzy matched``
            Best match found in *contacts*, or ``NaN`` if no match
            exceeded *score_cutoff*.
        ``Score``
            WRatio similarity score (``float``), or ``NaN``.
        ``Index``
            Row index of the match in *contacts* (``int``), or ``NaN``.

    Notes
    -----
    The output always contains exactly ``len(registrants)`` rows, whether
    or not a match was found.  Downstream functions (:func:`enrich_audience`)
    perform an inner join that silently drops unmatched rows.

    Examples
    --------
    >>> matched = fuzzy_match(registrants, contacts, score_cutoff=90)
    >>> matched[matched["Score"] < 100]       # approximate matches only
    >>> matched[matched["Score"].isna()]       # unmatched registrants
    """
    raw_results = registrants["Name"].apply(
        lambda name: extractOne(
            query=name,
            choices=contacts["Name"],
            score_cutoff=score_cutoff,
        )
    )

    result_df = pd.DataFrame(
        {
            "Name registrant": registrants["Name"].values,
            "Result": raw_results.values,
        }
    )
    result_df["Name fuzzy matched"] = result_df["Result"].apply(
        lambda x: x[0] if x is not None else None
    )
    result_df["Score"] = result_df["Result"].apply(
        lambda x: x[1] if x is not None else None
    )
    result_df["Index"] = result_df["Result"].apply(
        lambda x: x[2] if x is not None else None
    )

    return result_df.drop(columns=["Result"]).reset_index(drop=True)


# ===========================================================================
# Audience enrichment
# ===========================================================================


def enrich_audience(
    registrants: pd.DataFrame,
    contacts: pd.DataFrame,
    score_cutoff: float = 90.0,
    classify_position_fn: Optional[callable] = None,
    classify_company_fn: Optional[callable] = None,
) -> pd.DataFrame:
    """Enrich registrants with contact metadata from LinkedIn and congress sources.

    Chains :func:`fuzzy_match`, an inner join against *contacts*, optional
    whitespace normalisation of the ``Position`` column, and the optional
    application of job-title and company classifiers.

    Registrants that could not be matched (score below *score_cutoff*) are
    **silently excluded** from the returned DataFrame.  Use
    :func:`match_stats` to quantify and inspect unmatched registrants.

    Parameters
    ----------
    registrants : pd.DataFrame
        DataFrame produced by
        :func:`~audience_enrichment.loaders.load_registrants`.
        Must contain a ``Name`` column.
    contacts : pd.DataFrame
        Reference table produced by
        :func:`~audience_enrichment.loaders.build_contacts`.
        Must contain a ``Name`` column.
    score_cutoff : float, optional
        Similarity threshold forwarded to :func:`fuzzy_match`.
        Default is ``90.0``.
    classify_position_fn : callable, optional
        A callable with signature ``(position: str) -> str`` used to
        categorise job titles.  When provided, a ``Category_position``
        column is appended to the result.  Pass
        :func:`~audience_enrichment.classifiers.classify_position` or a
        custom function.  If ``None``, the column is not created.
    classify_company_fn : callable, optional
        A callable with signature ``(company: str) -> str`` used to
        categorise company names.  When provided, a ``Category_company``
        column is appended to the result.  Pass
        :func:`~audience_enrichment.classifiers.classify_company` or a
        custom function.  If ``None``, the column is not created.

    Returns
    -------
    pd.DataFrame
        Base columns (always present when available in *contacts*):
        ``Name``, ``Name registrant``, ``URL``, ``Email Address``,
        ``Company``, ``Position``.

        Optional columns (only present when the corresponding classifier
        is provided): ``Category_position``, ``Category_company``.

    Examples
    --------
    >>> # Without classifiers
    >>> audience = enrich_audience(registrants, contacts)

    >>> # With classifiers (adds Category_position and Category_company)
    >>> from audience_enrichment.classifiers import classify_position, classify_company
    >>> audience = enrich_audience(
    ...     registrants, contacts,
    ...     classify_position_fn=classify_position,
    ...     classify_company_fn=classify_company,
    ... )
    >>> audience.head()
    """
    # 1. Fuzzy matching
    matched = fuzzy_match(registrants, contacts, score_cutoff=score_cutoff)

    # 2. Join matched results against the contacts reference table
    audience = contacts.merge(
        matched,
        how="inner",
        left_on="Name",
        right_on="Name fuzzy matched",
    )

    # Strip whitespace from Position if the column exists
    if "Position" in audience.columns:
        audience["Position"] = audience["Position"].str.strip()

    # 3. Keep only the relevant columns
    base_cols = ["Name", "Name registrant", "URL", "Email Address", "Company", "Position"]
    existing_base_cols = [c for c in base_cols if c in audience.columns]
    enriched = audience[existing_base_cols].copy()

    # 4. Optional classification
    if classify_position_fn is not None and "Position" in enriched.columns:
        enriched["Category_position"] = (
            enriched["Position"]
            .apply(lambda x: classify_position_fn(str(x)))
        )

    if classify_company_fn is not None and "Company" in enriched.columns:
        enriched["Category_company"] = (
            enriched["Company"]
            .apply(lambda x: classify_company_fn(str(x)))
        )

    return enriched.reset_index(drop=True)


# ===========================================================================
# Matching statistics
# ===========================================================================


def match_stats(
    registrants: pd.DataFrame,
    audience: pd.DataFrame,
) -> dict[str, float | int]:
    """Compute coverage statistics for the fuzzy matching step.

    Compares the original registrant list against the enriched audience to
    report how many registrants were successfully matched and who was left
    out.  Intended to be called immediately after :func:`enrich_audience`.

    Parameters
    ----------
    registrants : pd.DataFrame
        Original registrant DataFrame **before** matching (as produced by
        :func:`~audience_enrichment.loaders.load_registrants`).
        Must contain a ``Name`` column.
    audience : pd.DataFrame
        Enriched DataFrame returned by :func:`enrich_audience`.
        Must contain a ``Name registrant`` column.

    Returns
    -------
    dict
        A dictionary with the following keys:

        ``n_registered`` : int
            Total number of registrants in the input list.
        ``n_matched`` : int
            Number of registrants successfully matched to a contact.
        ``n_unmatched`` : int
            Number of registrants for whom no match was found.
        ``pct_matched`` : float
            Match rate as a percentage in ``[0, 100]``, rounded to 2 d.p.
        ``pct_unmatched`` : float
            Unmatch rate as a percentage in ``[0, 100]``, rounded to 2 d.p.
        ``unmatched_names`` : list[str]
            Sorted list of registrant names that were not matched.

    Notes
    -----
    ``pct_matched + pct_unmatched == 100.0`` is guaranteed (within
    floating-point rounding).  When *registrants* is empty, both
    percentages are ``0.0`` and no division by zero occurs.

    Examples
    --------
    >>> stats = match_stats(registrants, audience)
    >>> print(f"Match rate  : {stats['pct_matched']:.1f}%")
    >>> print(f"Unmatched   : {stats['n_unmatched']}")
    >>> print("Names missed:", stats["unmatched_names"])
    """
    n_registered = len(registrants)
    n_matched = len(audience)
    n_unmatched = n_registered - n_matched

    matched_names = set(audience.get("Name registrant", pd.Series(dtype=str)).dropna())
    unmatched_names = list(
        np.setdiff1d(registrants["Name"].values, list(matched_names))
    )

    return {
        "n_registered": n_registered,
        "n_matched": n_matched,
        "n_unmatched": n_unmatched,
        "pct_matched": round(100 * n_matched / n_registered, 2) if n_registered else 0.0,
        "pct_unmatched": round(100 * n_unmatched / n_registered, 2) if n_registered else 0.0,
        "unmatched_names": unmatched_names,
    }


# ===========================================================================
# Audience filtering
# ===========================================================================


def filter_audience(
    audience: pd.DataFrame,
    positions: Optional[list[str]] = None,
    companies: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Filter the enriched audience by job-title and/or company category.

    Both filters are applied simultaneously with a logical AND: a row is
    kept only if it satisfies **all** provided criteria.  Passing ``None``
    for a criterion skips the corresponding filter entirely.

    .. important::
       This function requires that :func:`enrich_audience` was called with
       the appropriate classifiers.  Filtering on *positions* requires
       ``Category_position`` to be present; filtering on *companies*
       requires ``Category_company``.

    Parameters
    ----------
    audience : pd.DataFrame
        DataFrame returned by :func:`enrich_audience`, optionally
        containing ``Category_position`` and/or ``Category_company``
        columns (added when classifiers are passed to
        :func:`enrich_audience`).
    positions : list[str], optional
        Accepted values for the ``Category_position`` column
        (e.g. ``["Directeur", "Manager"]``).
        If ``None``, no filter is applied on job titles.
    companies : list[str], optional
        Accepted values for the ``Category_company`` column
        (e.g. ``["Assurance", "Réassurance"]``).
        If ``None``, no filter is applied on companies.

    Returns
    -------
    pd.DataFrame
        Subset of *audience* where all provided criteria are satisfied.
        The index is reset.  Returns an empty DataFrame (not an error)
        when no row matches.

    Raises
    ------
    KeyError
        If *positions* is not ``None`` but ``Category_position`` is absent
        from *audience* (classifier was not passed to
        :func:`enrich_audience`).
    KeyError
        If *companies* is not ``None`` but ``Category_company`` is absent
        from *audience*.

    Examples
    --------
    >>> # Decision-makers in insurance and reinsurance
    >>> decision_makers = filter_audience(
    ...     audience,
    ...     positions=["Directeur", "Manager"],
    ...     companies=["Assurance", "Réassurance"],
    ... )

    >>> # All contacts in consulting, regardless of seniority
    >>> consultants = filter_audience(audience, companies=["Cabinet de conseil"])
    """
    mask = pd.Series(True, index=audience.index)

    if positions is not None:
        if "Category_position" not in audience.columns:
            raise KeyError(
                "'Category_position' column is missing. "
                "Pass a classifier to enrich_audience()."
            )
        mask &= audience["Category_position"].isin(positions)

    if companies is not None:
        if "Category_company" not in audience.columns:
            raise KeyError(
                "'Category_company' column is missing. "
                "Pass a classifier to enrich_audience()."
            )
        mask &= audience["Category_company"].isin(companies)

    return audience.loc[mask].reset_index(drop=True)
