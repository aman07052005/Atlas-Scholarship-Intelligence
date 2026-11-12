# Extraction pipeline repair

## What changed

- HTML extraction removes navigation, header, footer, forms, scripts, styles and sidebars before extracting text from `main`, `article`, or the page body.
- PDF extraction uses embedded PDF metadata only when it is a meaningful title. A URL filename such as `FAQforICAR_NTS_PG_3104.pdf` is never automatically used as the scholarship name.
- Candidate identification now requires both (a) a meaningful scheme-like title/heading and (b) substantive scheme text such as eligibility, income, benefit, or education-level information.
- Generic portal/directory pages are retained as `SOURCE_PAGE` and get `scholarship_name = "Not specified"`; they are not presented as scholarship candidates.
- FAQ extraction pairs numbered questions with their answers, including flattened PDF text and entries without preserved line breaks. Question headings are never treated as answers. Amount extraction requires benefit-specific context; family-income ceilings cannot become scholarship benefits. Closing dates require an explicit deadline phrase and a date.
- Each extracted field retains a field-specific evidence excerpt containing its source URL and, for FAQs, both the question and answer. Renewal answers with CGPA/OGPA thresholds also populate academic requirements. Document requirements and application-route answers are retained where present. All live candidates remain human-review-required.
- Repeated crawls upsert one current review candidate per source URL; snapshots and page-change events preserve crawl history. Existing duplicate review rows are consolidated during database initialization.
- The crawler stores non-scheme pages with review status `NOT_A_SCHEME` so the discovery audit trail remains inspectable without promoting them into scholarship records.

## Verification performed in this workspace

- `python -m pytest -q`: **29 passed**.
- `python -m compileall -q src app.py`: passed.
- `python scripts/validate_package.py`: passed (29 records, 18 official-evidence-backed records, 10 VERIFIED ≥95 with mandatory gates, 93 evidence rows, 16 official source-register entries, 2 official change events, 4 stale/expired examples, 7 source types).
- Repeated-crawl tests: passed; changing the local fixture page creates a persisted page-hash event, while repeated source URLs update one review-queue row.
- `python scripts/run_local_fixture.py`: passed; one local page discovered/fetched and a review-required candidate persisted.

## Important limits

- These tests include controlled fixtures for portal navigation, a official ICAR FAQ question/answer layout, flattened PDF text, question-only FAQ rejection, a generic FAQ, field-specific snippets, and HTML navigation removal. They establish the intended extraction behavior on those fixtures, not perfect extraction across every government website or PDF layout.
- The fresh external crawler run in this build discovered/fetched 0 pages because DNS resolution failed for the four official hosts while checking `robots.txt`. The genuine run log is included; no external success is claimed.
- Streamlit could not be installed in this network-restricted build environment, so the redesigned UI still requires a Windows browser acceptance run. Dependencies are declared in `requirements.txt`.

## Windows update

Extract this package into a new folder, install requirements, and run `python -m pytest -q` plus `python scripts/validate_package.py`. Then run `python scripts/run_live_crawl.py` and `streamlit run app.py`. No source edits are required for these acceptance steps. The live external crawl and browser acceptance still need to be performed on the Windows machine. Keep all live candidates as `REVIEW_REQUIRED` until a human checks the actual scheme guideline and each extracted field.
