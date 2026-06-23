# audience_enrichment

Python package to **enrich a list of registrants** by crossing multiple data source : LinkedIn exports, Congress lists, and Livestorm / Teams exports.

---

## Installation

Install dependencies.

```bash
uv sync --all-groups
```

Install package (editable mode) for development. 

```bash
uv pip install -e .
```

TO DO: Install from GitHub
Install package for "production". 

```bash
XXX
```

Dependencies (`pandas`, `rapidfuzz`, `openpyxl`) are automatically installed.

---

## Package structure

```
audience_enrichment/
├── __init__.py        # expose public API
├── classifiers.py     # homemade classifiers for jobs and companies
├── loaders.py         # data loading and cleaning
└── enrichment.py      # fuzzy matching, enrichement, stats, filtration
```

---

## Usage

### 0. Gather data

Before using the package, you must create a “data” folder—for example, at the root of the project—and place the files from [SharePoint](https://detralytics.sharepoint.com/sites/DetraSharePoint/Shared%20Documents/Forms/AllItems.aspx?id=%2Fsites%2FDetraSharePoint%2FShared%20Documents%2FLearning%20%2D%20R%26D%2F07%20Innovation%20Lab%2F02%5FInternal%20R%26D%2F2%20%2D%20Projects%2FTarget%20audience%20via%20Linkedin&viewid=167bef3e%2D6436%2D439c%2Db2c2%2D5917e6f0c874) in it.

### 1. Loading data sources

```python
from audience_enrichment import loaders

# LinkedIn exports (one or more Connections*.csv)
connections = loaders.load_linkedin_connections(directory="./data")

# List of congress attendees (Excel, "Résumé" sheet)
congress = loaders.load_congress_list("Participants congrès 2026.xlsx")

# Livestorm L&L registrants (CSV, allows glob pattern)
registrants = loaders.load_registrants("livestorm-registrants-*.csv")

contacts = loaders.build_contacts(connections, congress)
```

### 2. Enrich registrants list

```python
from audience_enrichment import enrichment

# Without classifiers (missing Category_* columns)
audience = enrichment.enrich_audience(registrants, contacts)

# With custom classifiers
from classifiers import classify_position, classify_company

audience = enrichment.enrich_audience(
    registrants,
    contacts,
    score_cutoff=90,                    
    classify_position_fn=classify_position,
    classify_company_fn=classify_company,
)
```

### 3. Matching statistics

```python
stats = enrichment.match_stats(registrants, audience)

print(f"Matching rate  : {stats['pct_matched']}%")
print(f"Number of unmatched : {stats['n_unmatched']}")
print("Names of unmatched :", stats["unmatched_names"])
```

### 4. Filtering of the audience

```python
decision_makers = enrichment.filter_audience(
    audience,
    positions=["Directeur", "Manager"],
    companies=["Assurance", "Réassurance"],
)
```
