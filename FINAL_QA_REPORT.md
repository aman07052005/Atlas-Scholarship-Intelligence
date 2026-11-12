# Final QA Report — Atlas Scholarship Intelligence

**Build date:** 11 November 2026  
**Package state:** Submission candidate; local tests and package checks pass. Target-machine browser acceptance remains outstanding. External crawl/browser acceptance remains pending on the target Windows machine because this build runtime cannot resolve the public official-source hosts.

## Verified in this build

| Requirement | Result | Evidence |
|---|---|---|
| Python syntax | PASS | `python -m compileall -q src app.py scripts` |
| Automated tests | PASS | `python -m pytest -q`: **31 passed** |
| Package validation | PASS | `python scripts/validate_package.py` |
| Unique scholarship records | PASS | 29 unique records |
| Official-source-backed scholarship records | PASS | 18 records with allow-listed official primary-source field evidence (minimum 15) |
| Strict VERIFIED records | PASS | 10 records score ≥95 and pass all mandatory gates |
| Field-level evidence | PASS | 93 rows with source URL and excerpt |
| Official source register | PASS | 28 entries across 26 distinct official HTTPS URLs |
| Distinct scheme-specific primary URLs | PASS | 21 URLs assigned to records (minimum 15), across 10 publisher domains |
| Current-cycle source separation | PASS | `current_cycle_source_url` stored independently from scheme and guideline URLs |\n| Source diversity | PASS | 7 source types |
| Official change history | PASS | 2 dated official notification events |
| Stale/expired examples | PASS | 4 source-linked examples; minimum 2 |
| Local crawler integration | PASS | Local HTTP fixture discovers, fetches, extracts and persists a review-required candidate |
| Repeated-crawl change detection | PASS | Test changes a local source page between runs and confirms a page-hash change event is persisted |
| Review queue de-duplication | PASS | Repeated crawls update one candidate row per source URL; page snapshots retain history |
| FAQ extraction regression | PASS | ICAR FAQ explicit answers, flattened text, question-only rejection, amount, eligibility, renewal, academic, application route and documents are covered |
| SQLite lifecycle | PASS | Connections commit/rollback and close deterministically |
| ZIP integrity | PASS | Final archive tested with `unzip -t`; extracted copy re-tested |
| External live crawl | PARTIAL PASS | Target Windows run discovered 83 URLs and fetched 60; Social Justice and Tribal Affairs seed domains were refused because `robots.txt` could not be verified |
| Streamlit browser acceptance | PENDING | Must launch on the user's Windows machine and inspect the interactive UI and candidate review flow |

## Verification engine hardening

The confidence score is deterministic evidence coverage, not a truth probability. A numerical score alone cannot promote a record. `VERIFIED` requires **score ≥95** plus all mandatory gates:

1. HTTPS source host is on the explicit official-domain allow-list.
2. A scheme-specific official guideline/page exists; generic portal landing pages do not qualify.
3. Eligibility has field-level official evidence and a non-empty excerpt.
4. Benefit/amount has field-level official evidence and a non-empty excerpt.
5. Current-cycle/status evidence is dated and no older than 180 days.
6. At least three distinct fields are traceable to official sources.
7. No known conflict and no non-official evidence rows are present.

The official application URL and captured route excerpt contribute separate points. They are not mandatory when no official application route is available. Conflicts force `REVIEW_REQUIRED` and cap the score below 95. Tests cover bare-score rejection, missing benefit, conflicting sources, stale evidence and generic portal URLs.

## Crawler and UI

The crawler respects `robots.txt`, rate limits requests, filters malformed `/null` and `/Institutes` discovery URLs, stores page snapshots and candidate payloads, upserts the review candidate by source URL, and records page-hash changes across repeated successful crawls in `page_change_events`. FAQ question headings are separated from answers and each field keeps a question/answer evidence excerpt. Live candidates remain `REVIEW_REQUIRED`; they are not silently imported or promoted.

The redesigned Streamlit UI includes overview KPIs and charts, multi-filter scholarship explorer, record details, gate-by-gate score explanation, field-level source evidence, live crawler and candidate review queue, field/page change intelligence, stale-source register, and CSV/SQLite exports.

## External acceptance limitation

The target Windows machine completed an external run of `python scripts/run_live_crawl.py`: 83 URLs discovered and 60 fetched. Two seed domains were refused because `robots.txt` could not be verified (Social Justice HTTP 503; Tribal Affairs TLS certificate verification failure). These refusals are recorded in `logs/live_crawl_latest.json`; the crawler did not bypass them. The local HTTP fixture separately validates crawler mechanics.

## Windows acceptance commands (no source edits required)

Run these from the extracted project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/validate_package.py
python scripts/run_local_fixture.py
python scripts/run_live_crawl.py
streamlit run app.py
```

The live-crawl command must show at least one fetched page before claiming a successful external crawl. In Streamlit, inspect a newly discovered candidate, its source URL and evidence excerpts, then run the same crawl again after a source change to demonstrate page-hash detection. No manual code edits should be needed for these acceptance steps.


## Source-mapping update — 11 November 2026

Nine distinct official scheme documents were mapped to matching scholarship records. The database now stores `official_source_url`, `scheme_guideline_url`, and `current_cycle_source_url` separately. The current-cycle field is used for portal dates/status and is not misrepresented as scheme-specific rules. The 11 mapped scholarship rows retain their pre-update confidence score, verification status, lifecycle status and conflict flag. No new field evidence was fabricated.

The package contains 21 distinct non-directory scheme-specific primary URLs assigned across 10 publisher domains. The official source register contains 28 entries across 26 distinct URLs. Multiple scheme documents hosted on the NSP domain are counted as distinct documents/URLs, not as separate publisher domains. Historical guideline caveats are recorded in the source register and verification matrix.

## Final remaining human acceptance

The only remaining release acceptance item is to launch the Streamlit UI on the target Windows machine, inspect a scholarship detail page (including its three source links), inspect the live-crawler review queue, and optionally repeat the live crawl. The external crawler must continue to respect robots.txt; the two refused seed domains remain documented.
