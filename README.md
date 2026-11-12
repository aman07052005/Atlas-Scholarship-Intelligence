# Atlas Scholarship Intelligence

**An evidence-first scholarship discovery, extraction, verification, and change-monitoring platform for Indian scholarship programmes.**

Developed for the **Edxso AI Engineer Intern – Assignment 2**.

[Watch Project Demo](https://drive.google.com/file/d/1BSRz7ux1nf4qNXMmPbNIIWqYdYEAtx3b/view)

---

## 1. Project Overview

Atlas Scholarship Intelligence is a research-oriented intelligence platform designed to make Indian scholarship information easier to discover, evaluate, and monitor.

Scholarship information is distributed across government portals, scheme guidelines, institutional websites, and application directories. Details such as eligibility, financial benefits, deadlines, and application procedures may be incomplete, outdated, or inconsistent across sources.

Atlas addresses this challenge through a structured pipeline that combines scholarship discovery, field-level evidence collection, source mapping, confidence scoring, verification gates, and change monitoring.

The platform prioritizes **traceable evidence over unsupported automation**. A scholarship is not marked verified simply because information has been extracted or a source URL has been found.

## 2. Key Features

### Scholarship discovery and exploration
- Structured repository of Indian scholarship programmes.
- Search and explore scholarship records.
- Organized eligibility, benefits, deadlines, and application information.
- Scheme-specific primary-source mapping.

### Evidence-based extraction
- Field-level evidence tracking.
- Source URL and evidence excerpt association.
- Structured scholarship data extraction.
- Separation of scheme guidelines, official scheme pages, and current-cycle sources.

### Verification and confidence scoring
- Confidence scores for scholarship records.
- Mandatory verification gates.
- Evidence-backed verification decisions.
- Human-review queue for records that do not meet all verification requirements.
- Explicit distinction between `VERIFIED` and `REVIEW_REQUIRED`.

### Live scholarship crawler
- URL discovery and page fetching.
- Local fixture crawling for repeatable testing.
- Candidate extraction and review workflow.
- Crawl-run logging and error reporting.
- Respect for website access restrictions.

### Change intelligence
- Tracks official scholarship information changes.
- Maintains change-event records.
- Supports stale-record monitoring.
- Helps identify information that may need re-verification.

## 3. Project Metrics

The packaged research snapshot contains:

| Metric | Result |
|---|---:|
| Scholarship records | 29 |
| Records marked VERIFIED | 10 |
| Records requiring review | 19 |
| Official-evidence-backed records | 18 |
| Field-level evidence rows | 93 |
| Distinct scheme-specific primary URLs | 21 |
| Official source types | 7 |
| Official change events | 2 |
| Automated tests passed | 31 |

These are research-snapshot and validation results, not claims of live application availability.

## 4. System Architecture

The application follows a modular pipeline:

1. **Discovery:** Collect scholarship-related source URLs.
2. **Fetching:** Retrieve accessible source content.
3. **Extraction:** Identify scholarship information and candidate fields.
4. **Evidence mapping:** Associate extracted fields with supporting source evidence.
5. **Verification:** Evaluate evidence, confidence, and mandatory gates.
6. **Persistence:** Store scholarship records, evidence, crawl history, and change events.
7. **Intelligence:** Present records, verification status, and changes through the Streamlit dashboard.

### Main components

| Component | Responsibility |
|---|---|
| `app.py` | Streamlit dashboard and application interface |
| `src/crawler.py` | Crawling, discovery, and import workflows |
| `src/extractor.py` | Scholarship information extraction |
| `src/verification.py` | Confidence scoring and verification gates |
| `src/database.py` | Database operations and persistence |
| `src/history.py` | Historical records and change intelligence |
| `schema.sql` | Database schema |
| `tests/` | Automated pipeline and verification tests |

## 5. Technology Stack

- **Language:** Python
- **Application interface:** Streamlit
- **Data storage:** SQLite
- **Data processing:** CSV and structured Python workflows
- **Web extraction:** HTTP-based fetching and HTML parsing
- **Testing:** pytest
- **Version control:** Git and GitHub

The project uses a modular structure to keep crawling, extraction, verification, persistence, and presentation responsibilities separate.

## 6. Verification Methodology

Atlas uses evidence-backed verification rather than relying solely on extracted text or source availability.

Each scholarship record is evaluated using its available supporting evidence and verification requirements.

The system distinguishes between:

- **VERIFIED:** The record satisfies the required verification conditions.
- **REVIEW_REQUIRED:** Evidence or one or more mandatory conditions remain insufficient.

An official source mapping does not automatically promote a scholarship to VERIFIED. Missing application-route evidence, conflicting information, or other unmet requirements can keep a record in the human-review queue.

## 7. Data and Source Strategy

The project maintains separate source roles:

- `official_source_url`: Scheme-specific official source.
- `scheme_guideline_url`: Governing scheme guideline or specification.
- `current_cycle_source_url`: Official current-cycle listing used for monitoring application status and deadlines.

Historical documents and FAQs are labelled accordingly. Generic directory listings are not treated as scheme-specific guidelines.

The repository includes structured source registers, field evidence, scholarship seed data, stale-record information, and official change-event records.

## 8. Installation and Local Setup

### Prerequisites

- Python installed
- Git installed
- PowerShell or another terminal

### Clone the repository

```bash
git clone https://github.com/aman07052005/Atlas-Scholarship-Intelligence.git
cd Atlas-Scholarship-Intelligence
```

### Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
pip install -r requirements.txt
```

### Launch the application

```powershell
streamlit run app.py --server.port 8503
```

Open:

`http://localhost:8503`

## 9. Testing and Validation

Run the automated test suite:

```powershell
python -m pytest -q
```

Run package validation:

```powershell
python scripts/validate_package.py
```

Run the local crawler fixture:

```powershell
python scripts/run_local_fixture.py
```

The package validation checks the scholarship repository, evidence data, source mapping, official change records, and Python syntax.

## 10. Responsible Crawling and Limitations

Atlas is designed with responsible source access in mind.

- It does not bypass robots.txt or access restrictions.
- Inaccessible pages are recorded as crawl errors.
- Extraction candidates are not automatically treated as verified scholarship records.
- Evidence gaps are retained for human review.
- External website availability and content can change.
- Current application eligibility and deadlines should always be checked against the relevant official source.

A successful crawl is not equivalent to successful verification.

## 11. Repository Structure

```text
Atlas-Scholarship-Intelligence/
│
├── app.py
├── schema.sql
├── requirements.txt
├── README.md
├── .gitignore
│
├── data/
│   ├── atlas.db
│   ├── scholarships_seed.csv
│   ├── field_evidence.csv
│   ├── official_source_register.csv
│   ├── official_change_events.csv
│   └── official_stale_records.csv
│
├── docs/
│   ├── DEMO_WALKTHROUGH.md
│   ├── TECHNICAL_NOTE.md
│   ├── SOURCE_EVIDENCE.md
│   ├── SOURCE_REGISTER.md
│   └── SCHEME_VERIFICATION_MATRIX.md
│
├── logs/
│
├── scripts/
│
├── src/
│   ├── crawler.py
│   ├── extractor.py
│   ├── verification.py
│   ├── database.py
│   ├── history.py
│   └── demo.py
│
└── tests/
    ├── test_pipeline.py
    └── test_verification.py
```

## 12. Project Demo

Watch the complete application walkthrough:

[Atlas Scholarship Intelligence – Demo Video](https://drive.google.com/file/d/1BSRz7ux1nf4qNXMmPbNIIWqYdYEAtx3b/view)

The demonstration covers:
- Dashboard overview
- Scholarship discovery and exploration
- Evidence-based verification and confidence scoring
- Live scholarship crawling
- Change detection and intelligence

## 13. Future Improvements

- Expand scholarship coverage across additional states and institutions.
- Improve extraction quality for complex PDF guidelines.
- Add more robust historical comparison and change classification.
- Expand automated source freshness monitoring.
- Improve reviewer workflows for unresolved evidence gaps.
- Add broader multilingual scholarship discovery.

---

**Author:** Aman Yadav  
**GitHub:** [aman07052005](https://github.com/aman07052005)

**Project:** Atlas Scholarship Intelligence  
**Assignment:** Edxso AI Engineer Intern – Assignment 2
