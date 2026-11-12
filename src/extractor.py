"""Conservative extraction of scholarship candidates from official pages/documents.

FAQ-aware, evidence-first extraction. A fetched URL is never auto-verified;
ambiguous or incomplete values remain "Not specified" and require human review.
"""
from __future__ import annotations

import re
from .verification import is_official_url

UNKNOWN = "Not specified"
GENERIC_TITLES = {
    "home", "homepage", "student corner", "all scholarships", "scholarships",
    "national scholarship portal", "nsp", "scheme", "schemes", "guidelines",
    "faq", "frequently asked questions", "institute", "institutes", "student services",
}
NAV_TERMS = re.compile(
    r"\b(aadhaar seva kendra|check aadhaar|site map|helpdesk|login|registration form|"
    r"public dashboard|find institutes|nsp otr|officers login|grievance redressal|"
    r"contact us|know your|virtual assistance|still learning)\b", re.I,
)
SCHEME_TERMS = re.compile(
    r"\b(scholarship|fellowship|financial assistance|stipend|studentship|fee reimbursement)\b", re.I,
)
# Accept Q. No. 1:, Q1:, Question 1:, including when PDF text extraction joins
# the marker to the preceding paragraph rather than preserving a line break.
QUESTION_MARKER = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:Q\s*\.?\s*(?:No\.?\s*)?\d+|Question\s+\d+)\s*[:.)-]?\s*"
)


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n:;.-")


def _valid_excerpt(value: str) -> bool:
    value = _clean(value)
    return bool(value and len(value) >= 12 and not NAV_TERMS.search(value))


def _faq_pairs(text: str) -> list[tuple[str, str]]:
    """Parse numbered FAQ entries even when no literal 'Answer:' label exists.

    Each numbered block is split at its first question mark. The remaining
    block is the answer, stopping before the next numbered question. This
    handles line-preserved PDFs and text extractors that flatten PDF lines.
    """
    source = str(text or "").replace("\r", "\n")
    matches = list(QUESTION_MARKER.finditer(source))
    pairs: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        block = source[match.end():block_end].strip()
        if not block:
            continue

        # Explicit labels are preferred, but are not required in government FAQs.
        labelled = re.search(r"\b(?:Answer|Ans)\s*[:.)-]\s*", block, re.I)
        if labelled:
            question = _clean(block[:labelled.start()])
            answer = _clean(block[labelled.end():])
        else:
            qmark = block.find("?")
            if qmark < 0:
                continue
            question = _clean(block[:qmark + 1])
            answer = _clean(block[qmark + 1:])
            # Remove PDF layout separators and repeated heading fragments.
            answer = re.sub(r"^(?:Answer|Ans)\s*[:.)-]\s*", "", answer, flags=re.I)

        # Reject question-only blocks; never store the question as its answer.
        if question and "?" not in question:
            question += "?"
        if question and _valid_excerpt(answer) and not QUESTION_MARKER.search(answer[:40]):
            pairs.append((question, answer))
    return pairs


def _faq_scheme_name(text: str) -> str:
    source = str(text or "")
    match = re.search(
        r"(?:Frequently\s+Asked\s+Questions|FAQs?)\s+(?:on|for|about)\s+"
        r"(.{3,180}?)(?=\s+(?:Q\s*\.?\s*(?:No\.?\s*)?\d+|Question\s+\d+)|[\n\r]|$)",
        source, re.I,
    )
    if match:
        name = _clean(match.group(1)).strip(" :-–.")
        if SCHEME_TERMS.search(name):
            return name
    return UNKNOWN


def _candidate_name(page: dict, text: str) -> str:
    # Known FAQ title may be embedded in extracted PDF text rather than metadata.
    icar = re.search(r"\bICAR\s+NTS\s*[-–]?\s*PG\s+Scholarship\b", text, re.I)
    if icar:
        return "ICAR NTS-PG Scholarship"
    title = _clean(page.get("title"))
    if (title and title.lower() not in GENERIC_TITLES and SCHEME_TERMS.search(title)
            and not NAV_TERMS.search(title)
            and not re.search(r"\b(?:frequently asked questions|FAQ)\b|\.pdf$", title, re.I)):
        return title[:180]
    faq_name = _faq_scheme_name(text)
    if faq_name != UNKNOWN:
        return faq_name[:180]
    lines = [_clean(x) for x in re.split(r"\n+|(?<=[.!?])\s+", text) if _clean(x)]
    for line in lines[:35]:
        if (SCHEME_TERMS.search(line) and len(line) <= 180 and len(line.split()) >= 3
                and not NAV_TERMS.search(line)
                and not re.search(r"\b(?:FAQ|frequently asked questions|contents)\b", line, re.I)):
            return line[:180]
    for heading in page.get("headings", [])[:12]:
        heading = _clean(heading)
        if SCHEME_TERMS.search(heading) and len(heading) <= 180 and not NAV_TERMS.search(heading):
            return heading[:180]
    return UNKNOWN


def _field_from_question(question: str) -> str | None:
    q = question.lower()
    if re.search(r"eligib|who (?:is )?eligible|who can apply|qualif|admission criteria", q):
        return "eligibility"
    if re.search(r"amount|how much|rate of scholarship|value of scholarship", q):
        return "amount_benefit"
    if re.search(r"continuation|renewal|evaluation process|good conduct", q):
        return "renewal_requirements"
    if re.search(r"document|certificate|upload", q):
        return "documents_required"
    if re.search(r"apply separately|how to apply|application process|application route", q):
        return "application_route"
    if re.search(r"selection process|how .* selected", q):
        return "selection_process"
    if re.search(r"academic performance|minimum.*(?:cgpa|ogpa|marks)|qualifying grade", q):
        return "academic_requirements"
    if re.search(r"income criteria|family income|annual income", q):
        return "income_criteria"
    if re.search(r"last date|closing date|deadline", q):
        return "closing_date"
    if re.search(r"opening date|application starts|applications open", q):
        return "opening_date"
    if re.search(r"education level|course level|degree programme", q):
        return "education_level"
    return None


def _split_sentences(text: str) -> list[str]:
    # Preserve semicolon-delimited clauses because government PDF answers often
    # pack eligibility and income rules into one long sentence.
    return [_clean(x) for x in re.split(r"(?<=[.!?])\s+|\n+", str(text or "")) if _clean(x)]


def _extract_fields(text: str) -> tuple[dict[str, str], list[dict[str, str]]]:
    fields: dict[str, str] = {}
    evidence: list[dict[str, str]] = []

    # FAQ answers are the strongest extraction unit; question headings are never
    # allowed to leak into field values.
    for question, answer in _faq_pairs(text):
        field = _field_from_question(question)
        if not field:
            continue
        value = answer[:700]
        if field in fields and value not in fields[field]:
            fields[field] = (fields[field] + " " + value)[:1000]
        else:
            fields[field] = value
        evidence.append({
            "field": field, "value": value,
            "evidence_excerpt": ("Question: " + question + " Answer: " + answer)[:1200],
            "evidence_type": "FAQ_QUESTION_ANSWER",
        })
        # A continuation answer can contain a separately meaningful academic
        # threshold. Preserve it as its own field with the same source context.
        if field == "renewal_requirements" and re.search(r"\b(?:CGPA|OGPA|minimum prescribed performance)\b", answer, re.I):
            academic = answer[:700]
            fields.setdefault("academic_requirements", academic)
            evidence.append({
                "field": "academic_requirements", "value": academic,
                "evidence_excerpt": ("Question: " + question + " Answer: " + answer)[:1200],
                "evidence_type": "FAQ_QUESTION_ANSWER",
            })

    # Fallback for non-FAQ pages and fields not covered by a matched FAQ question.
    patterns = {
        "income_criteria": re.compile(r"\b(?:family|parental|household|annual) income\b", re.I),
        "eligibility": re.compile(r"\b(?:eligibility|eligible students|eligible candidates|who can apply|students must|applicant must|securing admission)\b", re.I),
        "amount_benefit": re.compile(r"\b(?:scholarship amount|amount of scholarship|financial assistance|stipend|maintenance allowance|tuition fee|fee reimbursement)\b|₹|\bRs\.?\s*\d", re.I),
        "closing_date": re.compile(r"\b(?:last date|closing date|applications? close|apply on or before|deadline)\b", re.I),
        "opening_date": re.compile(r"\b(?:application starts|applications? open|opening date|start date)\b", re.I),
        "education_level": re.compile(r"\b(?:undergraduate|postgraduate|post-graduate|doctoral|Ph\.?\s*D\.?|class\s*(?:IX|X|11|12|9|10)|school students|master'?s degree)\b", re.I),
        "academic_requirements": re.compile(r"\b(?:CGPA|OGPA|academic performance|minimum marks|qualifying marks|grade point)\b", re.I),
        "renewal_requirements": re.compile(r"\b(?:renewal|continuation of scholarship|good conduct|punctuality)\b", re.I),
    }
    # If a page contains numbered FAQ blocks, do not scan the question headings
    # as standalone sentences. Scan only their answer text plus other text.
    faq_pairs = _faq_pairs(text)
    has_faq_markers = bool(QUESTION_MARKER.search(str(text or "")))
    scan_text = str(text or "")
    if has_faq_markers:
        # Never fall back to scanning numbered FAQ question headings as answers.
        scan_text = "\n".join(answer for _, answer in faq_pairs)
    for field, pattern in patterns.items():
        if field in fields:
            continue
        for sentence in _split_sentences(scan_text):
            if not pattern.search(sentence) or not _valid_excerpt(sentence):
                continue
            if field == "amount_benefit":
                # Family-income limits are not scholarship benefits. Require a
                # benefit-specific phrase, not merely any currency amount.
                if not re.search(r"scholarship amount|amount of scholarship|financial assistance|stipend|maintenance allowance|tuition fee|fee reimbursement|monthly scholarship|per month|per annum scholarship", sentence, re.I):
                    continue
            if field in {"closing_date", "opening_date"} and not re.search(r"\b(?:\d{1,2}[-/ ](?:\d{1,2}|[A-Za-z]{3,9})[-/, ]20\d{2}|20\d{2})\b", sentence):
                continue
            value = sentence[:700]
            fields[field] = value
            evidence.append({"field": field, "value": value, "evidence_excerpt": value[:900], "evidence_type": "LIVE_PAGE_EXCERPT"})
            break
    return fields, evidence


def extract_structured_candidate(page: dict, provider_hint: str = UNKNOWN) -> dict:
    text = str(page.get("text") or "")
    url = str(page.get("url") or "")
    name = _candidate_name(page, text)
    fields, evidence = _extract_fields(text)
    substantive = bool(set(fields) & {
        "eligibility", "income_criteria", "amount_benefit", "education_level",
        "academic_requirements", "renewal_requirements",
    })
    is_scheme = name != UNKNOWN and substantive
    provider = provider_hint
    if provider == UNKNOWN and re.search(r"\bICAR\b", name, re.I):
        provider = "Indian Council of Agricultural Research (ICAR)"
    result = {
        "scholarship_name": name if is_scheme else UNKNOWN,
        "provider": provider if is_scheme else UNKNOWN,
        "official_source_url": url,
        "application_url": UNKNOWN,
        "amount_benefit": fields.get("amount_benefit", UNKNOWN),
        "eligibility": fields.get("eligibility", UNKNOWN),
        "income_criteria": fields.get("income_criteria", UNKNOWN),
        "academic_requirements": fields.get("academic_requirements", UNKNOWN),
        "renewal_requirements": fields.get("renewal_requirements", UNKNOWN),
        "documents_required": fields.get("documents_required", UNKNOWN),
        "application_route": fields.get("application_route", UNKNOWN),
        "selection_process": fields.get("selection_process", UNKNOWN),
        "age_criteria": UNKNOWN,
        "closing_date": fields.get("closing_date", UNKNOWN),
        "opening_date": fields.get("opening_date", UNKNOWN),
        "education_level": fields.get("education_level", UNKNOWN),
        "field_evidence": [],
        "needs_human_review": True,
        "is_scheme_candidate": is_scheme,
        "candidate_type": "SCHEME_CANDIDATE" if is_scheme else "SOURCE_PAGE",
        "classification_reason": (
            "Identifiable scholarship title and substantive scheme-specific evidence found; human review still required."
            if is_scheme else
            "No reliable scheme title plus substantive eligibility/benefit evidence; retained as a source page, not a scholarship record."
        ),
    }
    for item in evidence:
        result["field_evidence"].append({
            "field": item["field"], "value": item["value"], "source_url": url,
            "evidence_excerpt": item["evidence_excerpt"], "evidence_type": item["evidence_type"],
        })
    result["source_type"] = "OFFICIAL_PRIMARY" if is_official_url(url) else "DISCOVERY_ONLY"
    result["official_source_verified"] = is_official_url(url)
    return result
