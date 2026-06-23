"""
audience_enrichment.classifiers
================================

Classifiers for job titles and company names.

This module exposes two independent classification functions used to
categorise the contacts retrieved after fuzzy matching:

- :func:`classify_position` — assigns a seniority / role tier to a raw
  job title string (e.g. *"Head of Pricing"* → ``"Directeur"``).
- :func:`classify_company` — assigns an industry segment to a company
  name (e.g. *"AXA"* → ``"Assurance"``).

Both functions apply a **priority-ordered, first-match** strategy:

1. A curated list of exact / partial known names (``KNOWN_COMPANIES``).
2. Compiled regular expressions covering the long tail of unlisted names
   (``RULES_POSITIONS``, ``RULES_COMPANIES``).
3. A hard-coded default returned when no rule fires.

.. note::
   ``KNOWN_COMPANIES`` is defined inline for portability.  For
   production use with a large and frequently-updated catalogue,
   consider externalising it to a YAML or CSV file loaded at import
   time.

Classification categories
--------------------------
**Positions** (in priority order):

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Category
     - Typical titles matched
   * - Etudiant
     - étudiant, student, master 2, bachelor, école d'…
   * - Stagiaire
     - stagiaire, intern, internship, trainee, stage
   * - Alternant
     - alternant, alternance, apprenti, contrat pro
   * - Directeur
     - directeur, head of, CEO, CTO, président, fondateur, VP
   * - Manager
     - manager, responsable, senior, expert, team lead
   * - Junior
     - *(default — no rule matched)*

**Companies** (in priority order):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Category
     - Examples
   * - Assurance
     - AXA, Allianz, MAIF, Ethias, BNP Paribas Cardif
   * - Réassurance
     - SCOR, QBE Re, Arch Reinsurance
   * - Courtier
     - Aon, WTW, Marsh, Gallagher
   * - Cabinet de conseil
     - Detralytics, Oliver Wyman, Nexialog, Addactis
   * - Scolaire
     - Universités, grandes écoles, lycées
   * - Autre
     - *(default — no rule matched)*
"""

import re

# ===========================================================================
# Position classification
# ===========================================================================

# ---------------------------------------------------------------------------
# Priority-ordered rules — (category, compiled_regex)
# ---------------------------------------------------------------------------

RULES_POSITIONS = [
    # ── Etudiant ────────────────────────────────────────────────────────────
    (
        "Etudiant",
        re.compile(
            r"""
            \b(
                étudiant | etudiant | student |
                élève | eleve |
                master\s+\d | bachelor |
                école\s+d | ecole\s+d
            )\b
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),

    # ── Stagiaire ────────────────────────────────────────────────────────────
    (
        "Stagiaire",
        re.compile(
            r"""
            \b(
                stagiaire | intern(?:ship)? | intern | trainee | stage
            )\b
            # Also catch common typos
            | inter?n?ship
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),

    # ── Alternant ────────────────────────────────────────────────────────────
    (
        "Alternant",
        re.compile(
            r"""
            \b(
                alternant | alternance | apprenti | apprentice |
                work[\s\-]study | contrat\s+pro
            )\b
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),

    # ── Directeur ────────────────────────────────────────────────────────────
    (
        "Directeur",
        re.compile(
            r"""
            \b(
                directeur | directrice | director |
                head\s+of | chief | cto | cfo | ceo | coo | cso |
                président | president | fondateur | founder |
                managing\s+partner | associé\s+gérant |
                professor | professeur |
                maître\s+de\s+conf |
                enseignant | chargé\s+de\s+cours |
                domain\s+lead | people\s+lead |
                vice[\s\-]?president | vp\b
            )\b
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),

    # ── Manager ──────────────────────────────────────────────────────────────
    (
        "Manager",
        re.compile(
            r"""
            \b(
                manager | managing |
                responsable | teamlead | team\s+lead | lead\b |
                senior | sénior |
                expert\b |
                supervise | superviseur |
                managing\s+partner | partner\b |
                gérant
            )\b
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),
]

#: Category returned when no position rule fires.
DEFAULT_POSITION_CATEGORY = "Junior"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_position(title: str) -> str:
    """Assign a seniority / role category to a raw job title.

    Rules are tested **in priority order** (Etudiant → Stagiaire →
    Alternant → Directeur → Manager).  The first matching rule wins.
    When no rule matches, ``"Junior"`` is returned as the default.

    Parameters
    ----------
    title : str
        Raw job title as it appears in the LinkedIn export or registrant
        list (e.g. ``"Head of Pricing"`` or ``"Stagiaire actuariat"``).
        May contain accented characters, mixed case, and extra whitespace.

    Returns
    -------
    str
        One of ``"Etudiant"``, ``"Stagiaire"``, ``"Alternant"``,
        ``"Directeur"``, ``"Manager"``, ``"Junior"``, or ``""``
        (empty string when *title* is blank).

    Examples
    --------
    >>> classify_position("Head of Pricing")
    'Directeur'
    >>> classify_position("Stagiaire actuariat")
    'Stagiaire'
    >>> classify_position("Actuaire non-vie")
    'Junior'
    >>> classify_position("")
    ''
    """
    if not title or not title.strip():
        return ""
    for category, pattern in RULES_POSITIONS:
        if pattern.search(title):
            return category
    return DEFAULT_POSITION_CATEGORY


# ===========================================================================
# Company classification
# ===========================================================================

# ---------------------------------------------------------------------------
# Curated catalogue of known companies (exact & partial matching)
# ---------------------------------------------------------------------------

KNOWN_COMPANIES = {
    # ── Insurers ─────────────────────────────────────────────────────────────
    "Assurance": {
        "société générale assurances", "bpce assurances", "axa", "axa en france",
        "axa belgium", "allianz", "allianz france", "allianz benelux",
        "allianz côte d'ivoire", "sanlamallianz côte d'ivoire",
        "maif", "ethias", "federale assurance-verzekering",
        "federale assurance", "belfius insurance", "crédit agricole assurances",
        "credit agricole assurances", "bnp paribas cardif", "groupe bpce",
        "kbc bank & verzekering", "kbc", "suravenir", "prévoir", "prevoir",
        "dkv belgium", "europ assistance", "ag insurance", "lourmel",
        "assurance d'assistance", "contassur - cac/cba",
        "contassur", "leadway assurance côte d'ivoire",
        "crecer seguros - compañía de seguros", "crecer seguros"
    },
    # ── Reinsurers ───────────────────────────────────────────────────────────
    "Réassurance": {
        "scor", "qbe re", "arch reinsurance (europe)", "arch reinsurance",
    },
    # ── Brokers ──────────────────────────────────────────────────────────────
    "Courtier": {
        "aon", "aon luxembourg", "wtw", "willis towers watson",
        "marsh", "gallagher",
    },
    # ── Consulting firms ─────────────────────────────────────────────────────
    "Cabinet de conseil": {
        "detralytics", "oliver wyman", "deloitte", "nexialog consulting",
        "nexialog", "prim'act", "addactis", "triple a - risk finance belgium",
        "triple a risk finance", "owl mind analytics", "statismatic lab",
        "meinay", "actualib'", "actualib", "nexyan", "fgas", "actu-alia"
    },
    # ── Academic / educational institutions ──────────────────────────────────
    "Scolaire": {
        "université de strasbourg", "université libre de bruxelles",
        "ulb", "ichec brussels management school", "ichec",
        "collège catholique anuarite", "cameroun, ministère de l'enseignement secondaire",
        "ministère de l'enseignement secondaire",
        "banque nationale de belgique (bnb) / national bank of belgium",
        "banque nationale de belgique", "national bank of belgium",
        "spuerkeess",
    },
}

# ---------------------------------------------------------------------------
# Regex fallback rules — (category, compiled_regex)
# ---------------------------------------------------------------------------

RULES_COMPANIES = [
    # ── Scolaire ─────────────────────────────────────────────────────────────
    (
        "Scolaire",
        re.compile(
            r"""
            \b(
                université | universite | university |
                école | ecole | school | collège | college |
                institut | institute | académie | academie | academy |
                lycée | lycee | enseignement | éducation | education |
                faculty | faculté | faculte | campus
            )\b
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),

    # ── Réassurance ──────────────────────────────────────────────────────────
    (
        "Réassurance",
        re.compile(
            r"""
            \b(
                réassurance | reassurance | reinsurance | ré\s*assurance |
                re\b(?=.*\bassur)  # "Re" suivi de "assur" dans le même titre
            )\b
            | \bre\b  # suffixe Re (ex: QBE Re, Arch Re)
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),

    # ── Courtier ─────────────────────────────────────────────────────────────
    (
        "Courtier",
        re.compile(
            r"""
            \b(
                courtier | courtage | broker | brokerage |
                aon | wtw | willis | marsh | gallagher | howden
            )\b
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),

    # ── Cabinet de conseil ───────────────────────────────────────────────────
    (
        "Cabinet de conseil",
        re.compile(
            r"""
            \b(
                conseil | consulting | consultancy | consultant |
                advisory | advisors | actuariel | actuarial |
                cabinet | analytics | lab\b | solutions
            )\b
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),

    # ── Assurance ────────────────────────────────────────────────────────────
    (
        "Assurance",
        re.compile(
            r"""
            \b(
                assurance | assurances | insurance | verzekering |
                seguros | assicurazione | mutuelle | prévoyance | prevoyance |
                garantie | protection | assistance
            )\b
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),
]

#: Category returned when no company rule fires.
DEFAULT_COMPANY_CATEGORY = "Autre"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_company(company: str) -> str:
    """Assign an industry-segment category to a company name.

    Classification proceeds in three passes, stopping at the first hit:

    1. **Exact match** — the normalised (lower-cased, stripped) company
       name is looked up in :data:`KNOWN_COMPANIES`.
    2. **Partial match** — checks whether any known name is a substring
       of the input or vice-versa (handles extra legal suffixes, etc.).
    3. **Regex fallback** — :data:`RULES_COMPANIES` patterns are tested
       in order against the original (non-normalised) string.

    If none of the three passes produces a hit, ``"Autre"`` is returned.

    Parameters
    ----------
    company : str
        Raw company name as it appears in the LinkedIn export or
        registrant list (e.g. ``"AXA en France"`` or ``"Detralytics"``).
        May contain accented characters, mixed case, and extra whitespace.

    Returns
    -------
    str
        One of ``"Assurance"``, ``"Réassurance"``, ``"Courtier"``,
        ``"Cabinet de conseil"``, ``"Scolaire"``, ``"Autre"``, or ``""``
        (empty string when *company* is blank).

    Examples
    --------
    >>> classify_company("AXA")
    'Assurance'
    >>> classify_company("Detralytics")
    'Cabinet de conseil'
    >>> classify_company("Munich Re International")
    'Réassurance'
    >>> classify_company("Entreprise Inconnue XYZ")
    'Autre'
    >>> classify_company("")
    ''
    """
    if not company or not company.strip():
        return ""

    normalized = company.strip().lower()

    # 1. Exact matches in known lists
    for category, names in KNOWN_COMPANIES.items():
        if normalized in names:
            return category

    # 2. Partial matches in known lists
    for category, names in KNOWN_COMPANIES.items():
        for known in names:
            if known in normalized or normalized in known:
                return category

    # 3. Regex Rules
    for category, pattern in RULES_COMPANIES:
        if pattern.search(company):
            return category

    return DEFAULT_COMPANY_CATEGORY
