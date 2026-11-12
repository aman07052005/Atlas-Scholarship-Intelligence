# Technical Note — Atlas Scholarship Intelligence
**Edxso AI Engineer Intern, Assignment 2 | Research snapshot: 10 November 2026**

## 1. Objective and architecture
Atlas is an evidence-first discovery and monitoring prototype for Indian scholarships. Its pipeline is: configurable seed URLs → link discovery → HTTP fetch → text extraction → field candidate extraction → human review → evidence-backed record storage → change history → Streamlit dashboard. SQLite stores scholarship records, field evidence, crawl runs, discovered URLs, page snapshots, extracted candidates and changes.

## 2. Technology choices
Python 3.10+, Requests, BeautifulSoup, pypdf, SQLite, pandas, Streamlit and pytest. All dependencies are free/open-source. No paid APIs or paid scraping service are required.

## 3. Discovery and extraction
The crawler follows scholarship/funding/student/guideline links from configurable public seeds. It records discovered URLs, HTTP results, page titles, timestamps and SHA-256 content hashes. The extractor proposes candidate names and only fills fields when a matching text pattern is found; it retains the exact matched snippet and source URL. Candidate records are persisted with `REVIEW_REQUIRED`. A page title is not automatically treated as proof that a scholarship exists. The local HTTP integration test validates discovery, fetch, extraction and persistence.

## 4. Primary-source verification and evidence
The curated snapshot contains 29 records, 93 field-evidence rows and a 28-entry official source register representing 26 distinct official HTTPS URLs. Three DEPwD scheme-specific pages are included as official programme summaries; detailed benefit and eligibility claims remain governed by the umbrella guideline and amendments. Field evidence stores scholarship, field, extracted value, source URL, excerpt, capture reference and document version. Source documents include current UGC scheme pages, PM-USP CSSS guidelines, OBC/EBC/DNT Top Class guidelines, DEPwD scholarship guidelines plus the 04 Sep 2025 amendment, ICAR NTS guidelines, MHA PMSS guidelines, Tribal Affairs scheme pages, Ministry/PIB notices and NSP AY 2026-27 listings.

Unknown details remain `Not specified`. Current cycle status is kept separate from scheme identity: a scheme can be verified as genuine but closed or not yet opened for the current cycle. The CSSS and NMMSS entries remain `REVIEW_REQUIRED` due to official-source deadline inconsistencies; neither side is silently discarded.

## 5. Confidence rubric
The deterministic evidence-coverage score is not a probability:
- Official primary source URL: 15
- Scheme-specific official guideline/page: 15
- Eligibility field evidence: 20
- Benefit field evidence: 15
- Official application URL: 5
- Application-route field evidence: 5
- Current-cycle/status evidence: 10
- Field-level traceability across at least three distinct official fields: 15
- Known conflict: 15-point penalty and a hard cap below 95

The application URL and route excerpt are separate signals. A URL by itself cannot prove the route is described in the source. Missing benefit or eligibility excerpts prevent the corresponding gate from passing. Numeric benefit values must be present in the captured excerpt (at least half of the value's numeric tokens); qualitative benefit descriptions must share meaningful terms with the excerpt. A score ≥95 is necessary but not sufficient. VERIFIED additionally requires all mandatory gates: official HTTPS source on the allow-list; scheme-specific official guideline/page; eligibility evidence; benefit evidence; dated current-cycle/status evidence no older than 180 days; at least three traceable official fields; and no known conflict or non-official evidence. Application URL and route evidence contribute points but are not mandatory if no official route is available. A bare score without gate results is always REVIEW_REQUIRED. The score explanation is shown in the dashboard.

## 6. Change detection and stale data
The change history stores old value, new value, evidence date, source URL, evidence text and change kind. Two genuine NMMSS deadline changes are documented by dated Ministry of Education PIB notifications: 30 Sep→31 Oct 2026 (01 Oct notice) and 31 Oct→15 Nov 2026 (31 Oct notice). These are notification-backed historical changes, not synthetic fixtures. Repeated live page crawls compare the latest successful snapshot hash for each URL. A changed hash creates a `page_change_events` row with old/new hashes, detection timestamp, titles and compact old/current text evidence; candidates remain review-required until a human confirms any field-level change. Expiry is derived from explicit student application deadlines and the research date, not institute verification deadlines.

## 7. Live-crawl execution and limitation
Official sources were retrieved and inspected through live web research. The app's external crawler was run on the target Windows machine against NSP, UGC, Social Justice and Tribal Affairs seed URLs. The genuine run discovered 83 URLs and fetched 60. Social Justice was refused because robots.txt returned HTTP 503; Tribal Affairs was refused because TLS certificate verification failed while retrieving robots.txt. The crawler correctly refused both domains rather than bypassing robots controls. The complete runtime log is included in `logs/live_crawl_latest.json`. The crawler is also end-to-end tested against a local HTTP fixture.

## 8. Responsible crawling
The crawler uses ordinary HTTP requests and a descriptive User-Agent. It does not bypass authentication, CAPTCHA or access controls. Operators should respect robots.txt, site terms, rate limits and reasonable request intervals. JavaScript-heavy sites may require manual review or an approved official API.


## 9. Source URL role separation and scheme-specific mapping

The database separates the scheme-specific `official_source_url`, governing `scheme_guideline_url`, and `current_cycle_source_url`. The NSP All-Scholarships directory remains a current-cycle monitor where appropriate; it is no longer reused as the scheme guideline for records with a distinct official document. Nine additional scheme documents were mapped for AICTE Pragati, AICTE Saksham, AICTE Swanath, Labour Ministry worker scholarships, ICAR NTS, PM-USP CSSS, ST Higher Education, PMSS Railways/RPF and NEC Merit. The records retain explicit historical/version caveats. The package has 21 distinct non-directory scheme-specific primary URLs assigned to records across 10 publisher domains. No evidence excerpts or confidence upgrades were invented during source mapping.
