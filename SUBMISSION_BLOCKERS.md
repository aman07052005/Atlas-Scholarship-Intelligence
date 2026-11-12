# Release acceptance checklist

## Automated checks completed in this package

- 31 automated tests pass (`python -m pytest -q`).
- Package validator passes: 29 unique scholarship records, 10 VERIFIED records at ≥95 with mandatory evidence gates, 18 official-evidence-backed records, 93 field-evidence rows, 2 official change events and 7 source types.
- Local HTTP integration crawl passes: 1 URL discovered, 1 page fetched, 1 candidate persisted, no errors. This is a functional fixture, not an external-source crawl.
- FAQ extraction regression coverage includes the official ICAR NTS-PG FAQ structure, explicit `Answer:` labels, flattened PDF text, question-only rejection, field-specific evidence, benefit extraction and renewal/academic/document/application-route answers.
- Review candidates are now maintained as one current row per source URL. Repeated crawls update that row; page snapshots and page-change events retain crawl history. Existing duplicate candidate rows are consolidated during database initialization.
- Python syntax checks pass. `schema.sql` and SQLite initialization include candidate-source uniqueness.

## Remaining acceptance checks on the user's Windows machine

1. Replace the project folder with this release package and install dependencies: `python -m pip install -r requirements.txt`.
2. Run `python -m pytest -q` and `python scripts/validate_package.py`.
3. Start the app with `streamlit run app.py`. The database initialization performs the candidate de-duplication migration.
4. A live crawl has been run: 83 URLs discovered and 60 fetched. Social Justice and Tribal Affairs were refused because `robots.txt` could not be verified. Inspect the ICAR NTS-PG FAQ candidate and confirm extracted answer fields and evidence; do not mark it VERIFIED automatically.
5. Run the same live crawl again. Confirm that the review queue does not gain another row for the same source URL, while page snapshots/change events continue to record observations. The automated tests cover this idempotency behaviour, but a repeated external Windows run has not yet been recorded.

The Windows run did report 60 fetched pages. Do not claim all four seed domains were crawled successfully: Social Justice and Tribal Affairs were refused because robots.txt could not be verified. Robots.txt restrictions, network availability and official-site changes remain external runtime conditions.


## Source-count qualification

The official source register contains 28 entries across 26 distinct official HTTPS URLs. The 29 scholarship records now reference 21 distinct non-directory scheme-specific primary URLs across 10 publisher domains. The validator enforces at least 15 distinct scheme-specific URLs assigned to records, not merely 15 rows or repeated copies of the NSP directory. Nine additional official scheme documents were mapped with version caveats; historical documents are not represented as current-cycle amendments.

## Remaining release blocker

Automated checks pass. The remaining submission acceptance is a manual Windows browser check: start Streamlit, inspect record detail/source links and the live candidate review queue. The external crawl's two robots/TLS refusals remain transparently documented and must not be described as successful crawls.
