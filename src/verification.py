"""Deterministic, evidence-based verification and lifecycle classification.

The score is documented evidence coverage, not a probability of truth. A record
is VERIFIED only at >=95/100 and only when every mandatory evidence gate passes.
"""
from urllib.parse import urlparse
from datetime import date, datetime, timezone
import re

OFFICIAL = (
    "scholarships.gov.in", "ugc.gov.in", "socialjustice.gov.in",
    "education.gov.in", "aicte-india.org", "pib.gov.in",
    "reliancefoundation.org", "hdfc.bank.in", "sitaramjindalfoundation.org",
    "tatacapital.com", "tata.com", "icar.gov.in", "necouncil.gov.in",
    "tribal.nic.in", "mha.gov.in", "labour.gov.in", "depwd.gov.in",
    "divyangjan.depwd.gov.in",
)
UNKNOWN = {
    "", "not specified", "not specified in nsp listing", "not specified in listing",
    "not specified in reviewed official listing", "see official guidelines",
    "as per official guidelines", "not available", "unknown", "n/a", "na",
}
GENERIC_PATHS = {"", "/", "/all-scholarships", "/home", "/schemes"}
MANDATORY_GATES = (
    "official_primary_source",
    "scheme_specific_official_guideline",
    "eligibility_field_evidence",
    "benefit_field_evidence",
    "current_cycle_or_status_evidence",
    "field_level_traceability_3_fields",
    "no_known_source_conflict",
)


def is_official_url(url):
    """Return True only for HTTPS URLs on an explicitly allow-listed host."""
    try:
        parsed = urlparse(str(url or "").strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        return parsed.scheme.lower() == "https" and any(
            host == domain or host.endswith("." + domain) for domain in OFFICIAL
        )
    except (TypeError, ValueError):
        return False


def _value_ok(value):
    return str(value or "").strip().lower() not in UNKNOWN


def _parse_date(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            parsed = datetime.strptime(raw[:25], fmt)
            return parsed.date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _rows(evidence_rows):
    out = []
    for row in evidence_rows or []:
        field = str(row.get("field_name", row.get("field", ""))).strip().lower()
        url = str(row.get("source_url", row.get("url", ""))).strip()
        excerpt = str(row.get("evidence_excerpt", row.get("excerpt", ""))).strip()
        value = str(row.get("field_value", row.get("value", excerpt))).strip()
        captured = row.get("captured_at", row.get("captured_on", row.get("captured_date", "")))
        if field and value and url and excerpt:
            out.append({"field": field, "url": url, "excerpt": excerpt, "value": value,
                        "captured_at": str(captured or "").strip()})
    return out


def _guideline_is_specific(record):
    guideline_url = str(record.get("scheme_guideline_url") or "").strip()
    if not guideline_url or not is_official_url(guideline_url):
        return False
    parsed = urlparse(guideline_url)
    path = (parsed.path or "").lower()
    official_url = str(record.get("official_source_url") or "").strip().rstrip("/")
    if path in GENERIC_PATHS:
        return False
    if guideline_url.rstrip("/") == official_url and path in GENERIC_PATHS:
        return False
    # A specific document/page path is required; a domain homepage is not enough.
    return len(path.strip("/")) >= 5 and path not in GENERIC_PATHS


def _fresh_evidence(rows, record, today):
    """Require a dated evidence capture no older than 180 days where dates exist."""
    candidates = [x for x in rows if x["field"] in {"current_status", "closing_date"}]
    if not candidates:
        return False
    record_date = _parse_date(record.get("research_capture_date") or record.get("last_verified"))
    for item in candidates:
        captured = _parse_date(item.get("captured_at")) or record_date
        # A source excerpt without any date is not sufficient evidence of freshness.
        if captured and 0 <= (today - captured).days <= 180:
            return True
    return False


def _benefit_supported(value, excerpt):
    """Conservatively require numeric amounts in the excerpt when the value has them."""
    value_text = str(value or "").strip()
    excerpt_text = str(excerpt or "").strip()
    if not _value_ok(value_text) or len(excerpt_text) < 12:
        return False
    if re.search(r"\b(?:see|refer to|as per)\b.*\b(?:guideline|document|official|portal)\b", value_text, re.I):
        return False
    numbers_in_value = set(re.findall(r"\d[\d,]*(?:\.\d+)?", value_text))
    numbers_in_excerpt = set(re.findall(r"\d[\d,]*(?:\.\d+)?", excerpt_text))
    if numbers_in_value:
        matched = numbers_in_value & numbers_in_excerpt
        return len(matched) >= max(1, (len(numbers_in_value) + 1) // 2)
    # Qualitative benefits are acceptable only when the excerpt shares meaningful
    # benefit terms, not merely generic words such as "scheme" or "support".
    stop = {"the", "and", "for", "as", "per", "with", "from", "under", "full", "official", "scheme"}
    terms = {x.lower() for x in re.findall(r"[A-Za-z]{4,}", value_text) if x.lower() not in stop}
    excerpt_terms = {x.lower() for x in re.findall(r"[A-Za-z]{4,}", excerpt_text)}
    return len(terms & excerpt_terms) >= 2


def confidence_breakdown(record, evidence_rows=None, today=None):
    """Calculate a deterministic evidence-coverage score and transparent checks.

    A verified record must have a secure official source, a scheme-specific
    official document/page, supported eligibility and benefit values, fresh
    current-cycle evidence, three traceable official fields, and no known conflict.
    Application links are scored but are not a mandatory gate when unavailable.
    """
    today = today or date.today()
    rows = _rows(evidence_rows)
    official_source = is_official_url(record.get("official_source_url"))
    guideline = _guideline_is_specific(record)
    official_rows = [x for x in rows if is_official_url(x["url"])]
    by_field = {}
    for item in official_rows:
        by_field.setdefault(item["field"], []).append(item)

    eligibility_rows = by_field.get("eligibility", []) + by_field.get("academic_requirements", [])
    eligibility = any(_value_ok(x["value"]) and len(x["excerpt"]) >= 12 for x in eligibility_rows)
    benefit_rows = by_field.get("amount_benefit", [])
    benefit = bool(benefit_rows) and all(
        _benefit_supported(x["value"], x["excerpt"]) for x in benefit_rows
    )
    application_url = bool(
        str(record.get("application_url") or "").strip()
        and is_official_url(record.get("application_url"))
    )
    application_evidence = any(
        _value_ok(x["value"]) and len(x["excerpt"]) >= 8
        for field in ("application_route", "application_url")
        for x in by_field.get(field, [])
    )
    current = _fresh_evidence(official_rows, record, today)
    traceable_fields = {x["field"] for x in official_rows}
    traceable = len(traceable_fields) >= 3 and all(is_official_url(x["url"]) for x in rows)
    conflict = str(record.get("source_conflict", "false")).strip().lower() in ("true", "1", "yes")
    non_official_evidence = any(not is_official_url(x["url"]) for x in rows)
    no_conflict = not conflict and not non_official_evidence

    checks = {
        "official_primary_source": (15, official_source),
        "scheme_specific_official_guideline": (15, guideline),
        "eligibility_field_evidence": (20, eligibility),
        "benefit_field_evidence": (15, benefit),
        "official_application_url": (5, application_url),
        "application_route_field_evidence": (5, application_evidence),
        "current_cycle_or_status_evidence": (10, current),
        "field_level_traceability_3_fields": (15, traceable),
        "no_known_source_conflict": (0, no_conflict),
    }
    score = sum(weight for weight, passed in checks.values() if passed)
    if conflict:
        score = max(0, score - 15)
    if conflict or non_official_evidence:
        score = min(score, 94)
    detailed = {key: {"weight": weight, "passed": passed}
                for key, (weight, passed) in checks.items()}
    detailed["mandatory_gates_passed"] = {
        "weight": 0,
        "passed": all(detailed.get(gate, {}).get("passed", False) for gate in MANDATORY_GATES),
    }
    return round(float(score), 1), detailed


def classify_verification(score, checks=None):
    """Require both >=95 and explicit passing mandatory gates.

    `checks` is intentionally required for promotion. A bare score cannot prove
    source provenance and therefore defaults to REVIEW_REQUIRED.
    """
    if checks is None or float(score) < 95:
        return "REVIEW_REQUIRED"
    gates_pass = all(checks.get(gate, {}).get("passed", False) for gate in MANDATORY_GATES)
    return "VERIFIED" if gates_pass else "REVIEW_REQUIRED"


def lifecycle_status(record, today=None):
    today = today or date.today()
    raw = str(record.get("closing_date", "") or "").strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            deadline = datetime.strptime(raw, fmt).date()
            if deadline < today:
                return "EXPIRED"
            if (deadline - today).days <= 30:
                return "EXPIRING_SOON"
            return "ACTIVE"
        except ValueError:
            pass
    observed = str(record.get("observed_status", "") or "").upper()
    allowed = {"ACTIVE", "EXPIRING_SOON", "EXPIRED", "REVIEW_REQUIRED",
               "NO_LONGER_VERIFIABLE", "NOT_YET_OPENED"}
    return observed if observed in allowed else "REVIEW_REQUIRED"


def explain_score(record, evidence_rows=None):
    score, checks = confidence_breakdown(record, evidence_rows)
    passed = [k for k, v in checks.items() if v["passed"]]
    failed = [k for k, v in checks.items() if not v["passed"]]
    conflict = str(record.get("source_conflict", "false")).lower() in ("true", "1", "yes")
    note = " Conflict penalty applied." if conflict else ""
    why = ("Evidence-coverage score (not a probability). Passed: " + ", ".join(passed) +
           ". Missing: " + (", ".join(failed) if failed else "none") + "." + note)
    return score, checks, why
