"""
audience_enrichment.loaders
============================

Data loading and cleaning for each upstream source.

This module handles the import, validation, and normalisation of the three
raw data sources used by the enrichment pipeline:

- **LinkedIn exports** — one or more CSV files (named ``Connections...csv``) downloaded
  from the LinkedIn website (My Network → Connections → Export).
- **Congress attendee list** — an Excel workbook (``.xlsx``) with a
  ``Résumé`` sheet containing columns ``Name``, ``Job``, ``Compagnie``.
- **Livestorm registrant export** — a CSV file (or glob pattern) produced
  by the Livestorm platform with columns ``Nom``, ``Prénom``, ``Email``, etc.

All functions normalise the ``Name`` column to the canonical
``LASTNAME, Firstname`` format required by the fuzzy matching step.

Name normalisation
------------------
The ``LASTNAME, Firstname`` format is chosen because:

* It is unambiguous regardless of cultural name-ordering conventions.
* Upper-casing the last name makes case-insensitive comparison straightforward.
* The comma separator is rarely present in names, reducing false matches.

.. code-block:: python

   # LinkedIn: "First Name" = "Jean", "Last Name" = "Dupont"
   Name = "DUPONT, Jean"

   # Livestorm: "Nom" = "Dupont", "Prénom" = "Jean"
   Name = "DUPONT, Jean"

Typical usage
-------------
>>> from audience_enrichment import loaders
>>>
>>> connections  = loaders.load_linkedin_connections("./data")
>>> congress     = loaders.load_congress_list("./data/Participants congrès 2026.xlsx")
>>> registrants  = loaders.load_registrants("./data/livestorm-registrants-*.csv")
>>>
>>> contacts     = loaders.build_contacts(connections, congress)
"""

from __future__ import annotations

import glob
import os

import pandas as pd


# ===========================================================================
# Internal constants
# ===========================================================================

_LINKEDIN_REQUIRED_COLS = {"First Name", "Last Name"}
_CONGRESS_SHEET = "Résumé"
_CONGRESS_RENAME = {"Job": "Position", "Compagnie": "Company"}


# ===========================================================================
# Individual source loaders
# ===========================================================================


def _read_linkedin_csv(filepath: str) -> pd.DataFrame:
    """Lit un CSV LinkedIn en détectant automatiquement le séparateur,
    l'encodage et les éventuelles lignes de notes en en-tête."""
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            # Lire les premières lignes brutes pour détecter sep et skiprows
            with open(filepath, encoding=encoding, errors="replace") as fh:
                lines = [fh.readline() for _ in range(10)]

            # Trouver la ligne contenant "First Name"
            skiprows = 0
            for i, line in enumerate(lines):
                if "First Name" in line:
                    skiprows = i
                    break

            # Détecter le séparateur : ";" ou ","
            header_line = lines[skiprows]
            sep = ";" if header_line.count(";") > header_line.count(",") else ","

            df = pd.read_csv(
                filepath,
                sep=sep,
                skiprows=skiprows,
                encoding=encoding,
                encoding_errors="replace",
            )

            # Vérifier que les colonnes requises sont présentes
            if _LINKEDIN_REQUIRED_COLS.issubset(set(df.columns)):
                return df

        except Exception:
            continue

    # Dernier recours : lecture brute sans détection
    return pd.read_csv(filepath, sep=None, engine="python",
                       encoding="utf-8", encoding_errors="replace")



def load_linkedin_connections(
    directory: str = ".",
    filename_pattern: str = "Connections*.csv",
) -> pd.DataFrame:
    """Load and consolidate all LinkedIn connection exports found in a directory.

    LinkedIn allows exporting your connections as one or more CSV files
    whose names typically start with ``Connections``.  This function auto-detects
    them via a glob pattern, concatenates them, removes duplicates, and
    normalises the ``Name`` column to ``LASTNAME, Firstname``.

    Parameters
    ----------
    directory : str, optional
        Directory to search for LinkedIn export files.
        Defaults to the current working directory (current working directory).
    filename_pattern : str, optional
        Glob pattern used to locate the files within *directory*.
        Override only if the files have a non-standard naming convention.
        Defaults to the pattern ``Connections`` followed by ``*.csv``.

    Returns
    -------
    pd.DataFrame
        Contains all original LinkedIn CSV columns
        (``First Name``, ``Last Name``, ``Email Address``, ``Company``,
        ``Position``, ``URL``, …) **plus** a normalised ``Name`` column.

        - The ``Connected On`` column is dropped if present.
        - Exact duplicate rows are removed.
        - Rows where ``Name`` could not be constructed are dropped.

    Raises
    ------
    FileNotFoundError
        If no file matching *filename_pattern* is found in *directory*.
    ValueError
        If a matched file does not contain the required
        ``First Name`` and/or ``Last Name`` columns.

    Examples
    --------
    >>> connections = load_linkedin_connections("./data")
    >>> connections[["Name", "Company", "Position"]].head()
    """
    pattern = os.path.join(directory, filename_pattern)
    files = glob.glob(pattern)

    if not files:
        raise FileNotFoundError(
            f"No LinkedIn file found matching pattern: {pattern!r}"
        )

    frames = []
    for f in files:
        # Les vrais exports LinkedIn contiennent 2-3 lignes de notes avant
        # les en-têtes réels (ex: "Notes:,,,,"). On détecte automatiquement
        # la ligne contenant "First Name" pour savoir combien en sauter.
        ext = os.path.splitext(f)[1].lower()
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(f)
        else:
            df = _read_linkedin_csv(f)
        missing = _LINKEDIN_REQUIRED_COLS - set(df.columns)
        if missing:
            raise ValueError(
                f"{f!r} is missing required columns: {missing}"
            )
        frames.append(df)

    linkedin = pd.concat(frames, ignore_index=True)

    # Drop the connection date column and remove duplicates
    linkedin = linkedin.drop(columns=["Connected On"], errors="ignore")
    linkedin = linkedin.drop_duplicates()

    # Build the normalised Name column: "LASTNAME, Firstname"
    linkedin["Name"] = (
        linkedin["Last Name"].str.upper().str.strip()
        + ", "
        + linkedin["First Name"].str.strip()
    )
    linkedin = linkedin.loc[~linkedin["Name"].isna()]

    return linkedin.reset_index(drop=True)


def load_congress_list(
    filepath: str,
    sheet_name: str = _CONGRESS_SHEET,
) -> pd.DataFrame:
    """Load the congress attendee list from an Excel workbook.

    Reads the ``Résumé`` sheet (or *sheet_name*) of the provided Excel
    file, renames ``Job`` → ``Position`` and ``Compagnie`` → ``Company``,
    and strips leading/trailing whitespace from ``Position``.

    Parameters
    ----------
    filepath : str
        Absolute or relative path to the Excel workbook (``*.xlsx``).
    sheet_name : str, optional
        Name of the worksheet to read.  Defaults to ``Résumé``.

    Returns
    -------
    pd.DataFrame
        Three columns: ``Name`` (str), ``Position`` (str), ``Company`` (str).

    Raises
    ------
    FileNotFoundError
        If *filepath* does not exist on disk.
    KeyError
        If the worksheet is missing the ``Name``, ``Job``, or
        ``Compagnie`` columns.

    Examples
    --------
    >>> congress = load_congress_list("./data/Participants congrès 2026.xlsx")
    >>> congress.head()
    """
    congress = pd.read_excel(filepath, sheet_name=sheet_name)

    required = {"Name", "Job", "Compagnie"}
    missing = required - set(congress.columns)
    if missing:
        raise KeyError(
            f"Missing columns in congress file: {missing}"
        )

    congress = congress[["Name", "Job", "Compagnie"]].rename(
        columns=_CONGRESS_RENAME
    )
    congress["Position"] = congress["Position"].str.strip()

    return congress.reset_index(drop=True)


def _read_csv_auto(filepath: str) -> pd.DataFrame:
    """Lit un CSV en détectant automatiquement le séparateur et l'encodage."""
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(filepath, encoding=encoding, errors="replace") as fh:
                first_line = fh.readline()
            sep = ";" if first_line.count(";") > first_line.count(",") else ","
            return pd.read_csv(filepath, sep=sep, encoding=encoding,
                               encoding_errors="replace")
        except Exception:
            continue
    return pd.read_csv(filepath, sep=None, engine="python",
                       encoding="utf-8", encoding_errors="replace")



def load_registrants(filepath: str) -> pd.DataFrame:
    """Load the event registrant list from a Livestorm CSV export.

    The file path can be an exact path or a glob pattern, which is useful
    when the filename contains a timestamp (e.g.
    ``"livestorm-registrants-2026-06-*.csv"``).  If multiple files match
    the pattern, only the **first** one is loaded.

    The ``Name`` column is constructed from ``Nom`` (uppercased) and
    ``Prénom``, separated by a comma, to match the LinkedIn normalisation
    format.

    Parameters
    ----------
    filepath : str
        Exact path or glob pattern pointing to the Livestorm CSV file(s).

    Returns
    -------
    pd.DataFrame
        Columns retained from the source file (when present):
        ``Email``, ``Name``, ``Pays (depuis IP)``,
        ``Date d'inscription``, ``Company``, ``Job title``.

    Raises
    ------
    FileNotFoundError
        If no file matches *filepath* / the glob pattern.
    KeyError
        If the matched file does not contain the ``Nom`` or ``Prénom``
        columns required to build the ``Name`` column.

    Examples
    --------
    >>> registrants = load_registrants("./data/livestorm-registrants-*.csv")
    >>> registrants[["Name", "Email", "Company"]].head()
    """
    files = glob.glob(filepath)
    if not files:
        raise FileNotFoundError(f"No file found: {filepath!r}")

    # Use the first file if several match the pattern
    ext = os.path.splitext(files[0])[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(files[0])
    else:
        # Détecter automatiquement le séparateur (,  ou ;) et l'encodage
        df = _read_csv_auto(files[0])

    # Détecter le format : français (Nom/Prénom) ou anglais (First Name/Last Name)
    has_fr = {"Nom", "Prénom"}.issubset(set(df.columns))
    has_en = {"First Name", "Last Name"}.issubset(set(df.columns))

    if not has_fr and not has_en:
        raise KeyError(
            f"Missing columns in registrants file. "
            f"Expected 'Nom'+'Prénom' (FR) or 'First Name'+'Last Name' (EN). "
            f"Found: {list(df.columns)}"
        )

    if has_fr:
        df["Name"] = (
            df["Nom"].str.upper().str.strip()
            + ", "
            + df["Prénom"].str.strip()
        )
    else:
        df["Name"] = (
            df["Last Name"].str.upper().str.strip()
            + ", "
            + df["First Name"].str.strip()
        )

    keep_cols = [
        "Email",
        "Name",
        "Pays (depuis IP)",
        "Date d'inscription",
        "Company",
        "Job title",
        "Position",  # format anglais Livestorm
    ]
    existing_cols = [c for c in keep_cols if c in df.columns]
    return df[existing_cols].reset_index(drop=True)


# ===========================================================================
# Contact table assembly
# ===========================================================================


def build_contacts(*sources: pd.DataFrame) -> pd.DataFrame:
    """Merge multiple contact sources into a single reference DataFrame.

    Concatenates the DataFrames passed as positional arguments — typically
    the outputs of :func:`load_linkedin_connections` and
    :func:`load_congress_list` — into a unified table suitable for fuzzy
    matching.

    Parameters
    ----------
    *sources : pd.DataFrame
        One or more DataFrames to merge.  Each must contain at least a
        ``Name`` column in ``LASTNAME, Firstname`` format.

    Returns
    -------
    pd.DataFrame
        Row-wise concatenation of all *sources* with a reset integer index.
        Column set is the union of all source columns; missing values are
        filled with ``NaN``.

    Raises
    ------
    ValueError
        If no source DataFrame is provided.
    ValueError
        If any source DataFrame does not contain a ``Name`` column.

    Examples
    --------
    >>> contacts = build_contacts(connections, congress)
    >>> contacts.shape
    (1523, 8)

    >>> # Single source is also valid
    >>> contacts = build_contacts(connections)
    """
    if not sources:
        raise ValueError("At least one data source is required.")

    for i, src in enumerate(sources):
        if "Name" not in src.columns:
            raise ValueError(
                f"Source #{i} does not contain a 'Name' column."
            )

    return pd.concat(sources, ignore_index=True)
