# Atlas Scholarship Intelligence

### Evidence-First Scholarship Discovery, Extraction, Verification & Change Intelligence Platform

**Edxso AI Engineer Intern — Assignment 2**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red?logo=streamlit)](https://streamlit.io/)
[![Database](https://img.shields.io/badge/Database-SQLite-blue)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-31%20Passed-success)](#testing-and-validation)
[![Status](https://img.shields.io/badge/Project-Completed-success)](#project-overview)

---

## 🎥 Project Demo

**Watch the complete end-to-end application demonstration:**

### [▶ WATCH ATLAS SCHOLARSHIP INTELLIGENCE — PROJECT DEMO](https://drive.google.com/file/d/1BSRz7ux1nf4qNXMmPbNIIWqYdYEAtx3b/view)

The demonstration covers:

- Interactive dashboard and scholarship analytics
- Scholarship discovery and exploration
- Evidence-based extraction and verification
- Confidence scoring and mandatory verification gates
- Live scholarship crawling
- Change detection and intelligence

---

## 1. Project Overview

Atlas Scholarship Intelligence is an evidence-first scholarship intelligence platform designed to discover, extract, verify, and monitor Indian scholarship programmes.

Scholarship information is distributed across government portals, scheme guidelines, institutional websites, and application directories. Important details such as eligibility criteria, financial benefits, deadlines, and application procedures can be incomplete, outdated, or inconsistent across sources.

Atlas addresses this challenge through a structured pipeline that combines:

- Scholarship discovery and structured extraction
- Field-level evidence collection
- Official-source mapping
- Confidence scoring and verification gates
- Historical tracking and change detection
- Human-review workflows for unresolved records

**Core principle:** Extracted information is not automatically considered verified. Every verification decision must satisfy the platform's evidence and mandatory-gate requirements.

---

## 2. Key Features

### 2.1 Scholarship Discovery & Exploration

- Structured repository of Indian scholarship programmes.
- Search and explore scholarship records.
- Organized eligibility, benefits, deadlines, and application information.
- Scheme-specific official-source mapping.
- Separate tracking of current-cycle information and historical guidelines.

### 2.2 Evidence-Based Information Extraction

- Structured extraction of scholarship information.
- Field-level evidence tracking.
- Source URL and evidence excerpt association.
- Evidence traceability for extracted fields.
- Separation of official scheme pages, governing guidelines, and current-cycle sources.

### 2.3 Confidence Scoring & Verification

- Confidence scoring for scholarship records.
- Mandatory verification gates.
- Evidence-backed verification decisions.
- Explicit distinction between `VERIFIED` and `REVIEW_REQUIRED`.
- Human-review queue for records with insufficient or unresolved evidence.
- Prevention of automatic verification based only on source mapping or extraction.

### 2.4 Live Scholarship Crawler

- URL discovery and accessible-page fetching.
- Local fixture crawling for repeatable testing.
- Candidate extraction and review workflow.
- Crawl-run logging and error reporting.
- Responsible handling of website access restrictions.

### 2.5 Change Intelligence

- Tracking of official scholarship information changes.
- Historical change-event records.
- Stale-record monitoring.
- Identification of information requiring re-verification.
- Support for monitoring scholarship status and application-cycle information.

---

## 3. Project Metrics

The validated research snapshot contains:

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

**Important:** These figures describe the packaged research snapshot. Official-evidence-backed records are not necessarily formally VERIFIED. Verification status depends on the complete evidence and mandatory-gate requirements.

---

## 4. System Architecture & Workflow

Atlas follows a modular, evidence-driven processing pipeline.

```text
          OFFICIAL SCHOLARSHIP SOURCES
                       |
                       v
              SOURCE DISCOVERY
                       |
                       v
                PAGE FETCHING
                       |
                       v
             INFORMATION EXTRACTION
                       |
                       v
              FIELD-LEVEL EVIDENCE
                       |
                       v
             CONFIDENCE EVALUATION
                       |
                       v
             MANDATORY VERIFICATION
                       |
              +--------+--------+
              |                 |
              v                 v
           VERIFIED       REVIEW_REQUIRED
              |                 |
              +--------+--------+
                       |
                       v
              SQLITE PERSISTENCE
                       |
                       v
             CHANGE INTELLIGENCE
                       |
                       v
             STREAMLIT DASHBOARD
```

### Processing stages

| Stage | Responsibility |
|---|---|
| Discovery | Identify scholarship-related source URLs. |
| Fetching | Retrieve accessible source content. |
| Extraction | Identify scholarship information and candidate fields. |
| Evidence mapping | Associate extracted fields with supporting evidence. |
| Verification | Evaluate confidence and mandatory conditions. |
| Persistence | Store records, evidence, crawl history, and change events. |
| Intelligence | Present scholarship information, verification status, and changes. |

---

## 5. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application and processing logic |
| Streamlit | Interactive web dashboard |
| SQLite | Structured data persistence |
| Pandas | Tabular data handling |
| HTML parsing and HTTP fetching | Web content extraction |
| CSV | Structured research and evidence datasets |
| Pytest | Automated testing |
| Git & GitHub | Version control and project hosting |

The application uses a modular architecture to separate crawling, extraction, verification, persistence, historical tracking, and presentation.

---

## 6. Verification Methodology

Atlas prioritizes traceable evidence over unsupported automation.

Each scholarship record is evaluated using its available supporting evidence and mandatory verification requirements.

### Verification statuses

**VERIFIED**

A record is marked `VERIFIED` only when the required verification conditions are satisfied.

**REVIEW_REQUIRED**

A record remains in the human-review queue when evidence is incomplete, conflicting, or insufficient to satisfy mandatory requirements.

### Evidence and source strategy

The platform maintains distinct source roles:

| Field | Description |
|---|---|
| `official_source_url` | Scheme-specific official page or document used as the primary source. |
| `scheme_guideline_url` | Governing scheme guideline or specification. |
| `current_cycle_source_url` | Official current-cycle listing used for application-status and deadline monitoring. |

Historical documents and FAQs are labelled accordingly. Generic directory listings are not treated as scheme-specific guidelines.

**Verification rule:** Finding an official URL or extracting a field does not independently establish that a scholarship record is verified.

---

## 7. Database & Data Organization

The project maintains structured scholarship information and supporting research datasets.

| File | Purpose |
|---|---|
| `data/atlas.db` | SQLite database containing application records and related data. |
| `data/scholarships_seed.csv` | Curated scholarship seed records. |
| `data/field_evidence.csv` | Field-level supporting evidence. |
| `data/official_source_register.csv` | Official source register. |
| `data/official_change_events.csv` | Recorded official information changes. |
| `data/official_stale_records.csv` | Stale-record tracking data. |

This separation supports traceability between scholarship records, evidence, official sources, and historical changes.

---

## 8. Installation & Local Setup

### Prerequisites

- Python 3.10 or later
- Git
- PowerShell, Command Prompt, or another terminal

### Step 1: Clone the repository

```bash
git clone https://github.com/aman07052005/Atlas-Scholarship-Intelligence.git
cd Atlas-Scholarship-Intelligence
```

### Step 2: Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Run the application

```powershell
streamlit run app.py --server.port 8503
```

### Step 5: Open the dashboard

Visit:

```text
http://localhost:8503
```

---

## 9. Testing & Package Validation

The project includes automated tests for pipeline behaviour and verification logic.

### Run the test suite

```powershell
python -m pytest -q
```

**Validated result:** 31 tests passed.

### Run package validation

```powershell
python scripts/validate_package.py
```

The package validator checks:

- Scholarship record integrity and uniqueness.
- Verification counts and confidence requirements.
- Official-evidence coverage.
- Scheme-specific primary-source mapping.
- Field-level evidence data.
- Official change-event data.
- Supported source types.
- Python syntax validity.

### Run the local crawler fixture

```powershell
python scripts/run_local_fixture.py
```

This supports repeatable local crawler testing without depending entirely on external websites.

---

## 10. Responsible Crawling & Limitations

Atlas is designed to handle source access responsibly.

- It does not bypass `robots.txt` or website access restrictions.
- Inaccessible pages are recorded as crawl errors.
- Extraction candidates are not automatically treated as verified records.
- Evidence gaps are retained for human review.
- External website availability and content may change.
- Current eligibility and application deadlines should always be checked against the relevant official source.

A successful crawl does not automatically imply successful extraction or verification.

---

## 11. Repository Structure

```text
Atlas-Scholarship-Intelligence/
│
├── .streamlit/
│   └── config.toml
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
│   ├── official_stale_records.csv
│   └── README.txt
│
├── docs/
│   ├── DEMO_WALKTHROUGH.md
│   ├── EXTRACTION_REPAIR.md
│   ├── SCHEME_VERIFICATION_MATRIX.md
│   ├── SOURCE_EVIDENCE.md
│   ├── SOURCE_REGISTER.md
│   └── TECHNICAL_NOTE.md
│
├── logs/
│   ├── live_crawl_latest.json
│   ├── local_fixture_crawl.json
│   └── official_web_research_capture.json
│
├── scripts/
│   ├── prepare_demo.py
│   ├── run_live_crawl.py
│   ├── run_local_fixture.py
│   ├── validate_package.py
│   └── verify_release.ps1
│
├── src/
│   ├── crawler.py
│   ├── database.py
│   ├── demo.py
│   ├── extractor.py
│   ├── history.py
│   └── verification.py
│
└── tests/
    ├── test_pipeline.py
    └── test_verification.py
```

---

## 12. Documentation

Additional project documentation is available in the `docs/` directory.

- **Technical Note:** Architecture, design decisions, pipeline, and implementation details.
- **Source Evidence:** Supporting evidence and source mapping.
- **Source Register:** Official scholarship source references.
- **Scheme Verification Matrix:** Scheme-level verification details.
- **Demo Walkthrough:** Application demonstration workflow.
- **Extraction Repair:** Extraction quality and repair documentation.

---

## 13. Future Improvements

Potential extensions include:

- Expanding scholarship coverage across additional states and institutions.
- Improving extraction quality for complex PDF guidelines.
- Enhancing historical comparison and change classification.
- Expanding automated source-freshness monitoring.
- Improving human-review workflows for unresolved evidence gaps.
- Supporting broader multilingual scholarship discovery.
- Adding more detailed reviewer analytics and reporting.

---

## 14. Project Links

| Resource | Link |
|---|---|
| GitHub Repository | [Atlas Scholarship Intelligence](https://github.com/aman07052005/Atlas-Scholarship-Intelligence) |
| Project Demo | [Watch the Demo](https://drive.google.com/file/d/1BSRz7ux1nf4qNXMmPbNIIWqYdYEAtx3b/view) |

---

## Author

**Aman Yadav**

GitHub: [@aman07052005](https://github.com/aman07052005)

**Project:** Atlas Scholarship Intelligence  
**Assignment:** Edxso AI Engineer Intern — Assignment 2

---

*Built with a focus on evidence traceability, responsible data collection, transparent verification, and reliable scholarship intelligence.*
