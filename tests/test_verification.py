from src.verification import confidence_breakdown,classify_verification,lifecycle_status,is_official_url
def test_official_domain():
    assert is_official_url("https://scholarships.gov.in/All-Scholarships")
    assert not is_official_url("https://example.com/")
def test_score_deterministic():
    r={"scholarship_name":"Test","provider":"Govt","official_source_url":"https://scholarships.gov.in/x","application_url":"https://scholarships.gov.in/app","eligibility":"Criteria documented","evidence":"Official evidence","closing_date":"30-11-2026","observed_status":"ACTIVE"}
    assert confidence_breakdown(r)[0]==confidence_breakdown(r)[0]
def test_threshold_requires_evidence_gates():
    assert classify_verification(95) == "REVIEW_REQUIRED"  # a number alone proves nothing
    checks = {name: {"passed": True} for name in (
        "official_primary_source", "scheme_specific_official_guideline",
        "eligibility_field_evidence", "benefit_field_evidence",
        "current_cycle_or_status_evidence", "field_level_traceability_3_fields",
        "no_known_source_conflict")}
    assert classify_verification(95, checks) == "VERIFIED"
    checks["benefit_field_evidence"]["passed"] = False
    assert classify_verification(100, checks) == "REVIEW_REQUIRED"
    assert classify_verification(94.99, checks) == "REVIEW_REQUIRED"
def test_missing_deadline_not_invented():
    assert lifecycle_status({"closing_date":"","observed_status":"REVIEW_REQUIRED"})=="REVIEW_REQUIRED"
