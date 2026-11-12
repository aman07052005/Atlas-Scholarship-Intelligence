# Extraction and review-queue repair QA

## Defects addressed

- FAQ question headings were previously misclassified as eligibility answers.
- FAQ parsing previously depended on a literal `Answer:` marker and failed on flattened PDF text.
- Benefit extraction could confuse family-income limits with scholarship amounts.
- The ICAR FAQ scheme title could be confused with the PDF filename or a question sentence.
- Repeated crawls inserted duplicate review-queue rows for the same source URL.

## Repair behaviour

- Numbered FAQ blocks are split into question/answer pairs, with or without line breaks. Explicit `Answer:` labels are supported; otherwise the first question mark separates the question from its answer.
- Question-only FAQ blocks are never treated as field values. If FAQ markers exist but no answer is available, fallback sentence extraction does not mine the question headings.
- Question intent maps answer text to eligibility, amount, renewal, academic requirements, income, dates, education level, documents, application route and selection process.
- A renewal answer containing a CGPA/OGPA threshold is also retained as academic evidence.
- Amount fallback requires benefit-specific context; an income ceiling alone cannot become a scholarship benefit.
- Every extracted field evidence row retains the source URL and a question-plus-answer excerpt.
- Candidates are upserted by source URL. Older duplicate rows are consolidated at database initialization; page snapshots and page-change events remain the crawl-history layer.
- Candidate extraction always requires human review. It does not itself confer VERIFIED status.

## Regression tests

The test suite includes the official ICAR NTS-PG FAQ's numbered question/answer layout, flattened text, question-only rejection, correct benefit and eligibility extraction, field-specific traceability, and repeated-crawl candidate de-duplication.
