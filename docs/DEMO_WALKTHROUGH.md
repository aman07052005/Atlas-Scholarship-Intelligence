# Demo Walkthrough — 4 to 5 minutes
1. Run `python scripts/prepare_demo.py`, then `streamlit run app.py`.
2. Show the redesigned overview KPI cards, verification/lifecycle/source charts, and filter the explorer by VERIFIED / REVIEW_REQUIRED, lifecycle and source type.
3. Open Ishan Uday. Show UGC source, eligibility, income, amount and field evidence.
4. Open one PwD scheme. Show the base DEPwD guideline and 04 Sep 2025 amendment evidence, including the UDID/Aadhaar update.
5. Open ICAR NTS-UG or NTS-PG. Show the scheme-specific guideline, its historical version caveat, and the separate NSP current-cycle source. Explain the ICAR NTS-PG amount conflict.
6. Open Change History. Show both dated NMMSS PIB deadline transitions and evidence URLs.
7. Show expired examples from NSP and explain that the student application deadline—not later institute verification—is used for expiry.
8. Open Live crawler & extractor. Run it on a network-enabled connection. Show discovered/fetched counts, candidate JSON, source snippets and review-required status. Do not present the build-runtime DNS failure as a successful live crawl.
9. Explain the evidence score, mandatory verification gates, 180-day freshness rule, official-source conflict penalty and why missing fields remain Not specified.
10. Re-run the same source in the local fixture/test environment to show page-hash change detection; then show `FINAL_QA_REPORT.md` and the logs folder. For the live demo, run the external crawl on a network-enabled machine.
