"""
tests/test_analysis.py
----------------------
Regression tests for demo-mode analysis and validator logic.
Run with: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.ai_service import _demo_mode_analysis
from services.validator import check_missing_fields, is_missing, validate_ai_response


# ── Helpers ───────────────────────────────────────────────────────────────────

def assert_missing(result, field):
    assert is_missing(result.get(field)), (
        f"Expected '{field}' to be missing/null, got: {result.get(field)!r}"
    )

def assert_present(result, field):
    assert not is_missing(result.get(field)), (
        f"Expected '{field}' to be present, got: {result.get(field)!r}"
    )


# ── Test 1: Unclear project-report email ─────────────────────────────────────

def test_unclear_project_report():
    text = (
        "Subject: Project Report\n\n"
        "Hi, please prepare the project report as soon as possible and share it "
        "with the team before the review. Include all the important details."
    )
    result = _demo_mode_analysis(text)

    # Title must not start with "Subject:" and must not be the full body
    assert not result["title"].lower().startswith("subject:"), \
        f"Title should not include subject line: {result['title']!r}"
    assert len(result["title"]) <= 70, f"Title too long: {result['title']!r}"

    # ASAP is not an explicit deadline
    assert_missing(result, "deadline")

    # Deliverable should be extracted (report)
    assert_present(result, "deliverable")
    assert "report" in result["deliverable"].lower(), \
        f"Expected 'report' in deliverable, got: {result['deliverable']!r}"

    # Owner not specified
    assert_missing(result, "owner")

    # Clarity check must flag missing deadline
    validation = check_missing_fields(result)
    assert validation["needs_clarification"], "Should need clarification"
    assert "deadline" in validation["missing_required"], "deadline must be flagged"

    # Clarification questions must exist
    assert len(result["clarification_questions"]) > 0

    # At least one question about deadline
    deadline_q = any(
        "deadline" in q.lower() or "date" in q.lower() or "exact" in q.lower()
        for q in result["clarification_questions"]
    )
    assert deadline_q, f"Expected a deadline question, got: {result['clarification_questions']}"


# ── Test 2: Clear request with explicit deadline ──────────────────────────────

def test_clear_request():
    text = (
        "Hi Alex,\n\n"
        "Please prepare a 2-page executive summary of the Q2 sales report by Friday 5pm.\n"
        "Owner: Alex Johnson\n\n"
        "Best regards, Linda"
    )
    result = _demo_mode_analysis(text)

    assert_present(result, "deadline")
    assert_present(result, "deliverable")

    # Title should not include greeting
    assert not result["title"].lower().startswith("hi"), \
        f"Title should not start with greeting: {result['title']!r}"


# ── Test 8: Clarification questions have no duplicated articles ───────────────

def test_no_duplicate_articles_in_questions():
    text = (
        "Subject: Project Report\n\n"
        "Hi, please prepare the project report as soon as possible and share it "
        "with the team before the review. Include all the important details."
    )
    result = _demo_mode_analysis(text)
    import re
    for q in result["clarification_questions"]:
        # Check for doubled articles/words: 'the the', 'a a', 'an an'
        assert not re.search(r'\b(the|a|an)\s+\1\b', q, re.IGNORECASE), \
            f"Duplicate article found in question: {q!r}"
        # Check for any consecutive duplicate words
        assert not re.search(r'\b(\w+)\s+\1\b', q, re.IGNORECASE), \
            f"Consecutive duplicate word found in question: {q!r}"


# ── Test 9: Clear request with specific requirements is not flagged ───────────

def test_clear_request_with_specific_requirements():
    text = (
        "Hi team,\n\n"
        "Please prepare the Q3 financial summary report by Wednesday EOD.\n"
        "The report must include revenue breakdown, cost analysis, and profit margins.\n"
        "Owner: Finance Team\n\n"
        "Thanks, Sarah"
    )
    result = _demo_mode_analysis(text)

    assert_present(result, "deadline")
    assert_present(result, "deliverable")
    assert_present(result, "owner")

    validation = check_missing_fields(result)
    assert not validation["needs_clarification"], (
        f"Clear request should not need clarification. Missing: {validation['missing_required']}, "
        f"Questions: {result['clarification_questions']}"
    )
    assert result["clarification_questions"] == [], \
        f"Expected no questions for clear request, got: {result['clarification_questions']}"


# ── Test 10: Weekly status report — full extraction ─────────────────────────

def test_weekly_status_report():
    text = (
        "Subject: Weekly Status Report\n\n"
        "Hi Team,\n\n"
        "Please prepare the weekly project status report using the attached template. "
        "Include completed tasks, pending tasks, current blockers, and next week plan. "
        "Save the report as a PDF and share it with the project team by 4:00 PM on 28 October 2026.\n\n"
        "Thanks,\nProject Manager"
    )
    result = _demo_mode_analysis(text)

    # Title: must start with the main action verb
    assert result["title"].lower().startswith("prepare"), \
        f"Title should start with 'prepare', got: {result['title']!r}"
    assert "status report" in result["title"].lower(), \
        f"Title should mention 'status report', got: {result['title']!r}"
    assert len(result["title"]) <= 80, f"Title too long: {result['title']!r}"

    # Deadline: normalized to "28 October 2026, 04:00 PM"
    deadline = result["deadline"]
    assert deadline is not None, "Deadline should be extracted"
    assert "October" in deadline, \
        f"Deadline should include 'October', got: {deadline!r}"
    assert "2026" in deadline, \
        f"Deadline should include year '2026', got: {deadline!r}"
    assert "28" in deadline, \
        f"Deadline should include day '28', got: {deadline!r}"
    assert "PM" in deadline.upper(), \
        f"Deadline should include time with AM/PM, got: {deadline!r}"
    # Must not contain raw trigger words
    assert not deadline.lower().startswith("by "), \
        f"Normalized deadline should not start with 'by', got: {deadline!r}"

    # Deliverable: must contain 'report' and 'PDF'
    deliverable = result["deliverable"]
    assert deliverable is not None, "Deliverable should be extracted"
    assert "report" in deliverable.lower(), \
        f"Deliverable should mention 'report', got: {deliverable!r}"
    assert "pdf" in deliverable.lower(), \
        f"Deliverable should mention PDF format, got: {deliverable!r}"
    assert "using" not in deliverable.lower(), \
        f"Deliverable should not contain 'using', got: {deliverable!r}"

    # Description: full original text preserved
    assert result["description"] == text.strip(), \
        f"Description should be the full original text. Got length {len(result['description'])} vs {len(text.strip())}"

    # Owner: not specified — but essentials are present so no clarification question
    assert_missing(result, "owner")
    assert result["clarification_questions"] == [], \
        f"No questions expected when essentials are present, got: {result['clarification_questions']}"

    # Validator: owner is optional, not a required blocker
    validation = check_missing_fields(result)
    assert not validation["needs_clarification"], \
        f"Should not need clarification when task+deliverable+deadline are present. Missing required: {validation['missing_required']}"
    assert "owner" in validation["missing_optional"], \
        f"Owner should appear as optional, got: {validation['missing_optional']}"


# ── Test 11: Unclear deadline (ASAP) does not match full-date pattern ─────────

def test_asap_does_not_produce_full_date():
    text = (
        "Subject: Project Report\n\n"
        "Hi, please prepare the project report as soon as possible and share it "
        "with the team before the review. Include all the important details."
    )
    result = _demo_mode_analysis(text)
    # ASAP must not be treated as an explicit deadline
    assert_missing(result, "deadline")
    # Must still ask a deadline question
    questions = result["clarification_questions"]
    assert any(
        "deadline" in q.lower() or "date" in q.lower() or "exact" in q.lower()
        for q in questions
    ), f"Expected deadline question, got: {questions}"


# ── Test 12: Deadline normalization ──────────────────────────────────────────

def test_deadline_normalization():
    from services.ai_service import _normalize_deadline
    cases = [
        ("by 4:00 pm on 28 october 2026",  "28 October 2026, 04:00 PM"),
        ("by october 28, 2026",             "28 October 2026"),
        ("by friday 5pm",                   "Friday, 5:00 PM"),
        ("by eod",                          "End of Day"),
        ("by next week",                    "Next Week"),
        ("by tomorrow",                     "Tomorrow"),
    ]
    for raw, expected in cases:
        result = _normalize_deadline(raw)
        assert result == expected, \
            f"_normalize_deadline({raw!r}) -> {result!r}, expected {expected!r}"

# ── Test 13: Suggested reply does not contaminate original request or title ─────

def test_suggested_reply_does_not_overwrite_original():
    """
    Regression test: generating a suggested reply must never change
    the original request text or the extracted task title.
    """
    original_email = (
        "Hi,\n\n"
        "Please update the dashboard before the next meeting. "
        "The metrics are outdated.\n\n"
        "Thanks,\nSarah"
    )
    result = _demo_mode_analysis(original_email)

    # Title must come from the original email, not the reply
    assert result["title"].lower().startswith("update"), \
        f"Title should start with 'update', got: {result['title']!r}"
    assert "dashboard" in result["title"].lower(), \
        f"Title should mention 'dashboard', got: {result['title']!r}"
    assert "happy" not in result["title"].lower(), \
        f"Title must not contain reply text, got: {result['title']!r}"
    assert "thank" not in result["title"].lower(), \
        f"Title must not contain reply text, got: {result['title']!r}"

    # Description must be the original email, not the suggested reply
    assert result["description"] == original_email.strip(), \
        f"Description must equal original email. Got: {result['description'][:80]!r}"
    assert result["description"] != result["suggested_reply"], \
        "Description must not equal suggested_reply"

    # Suggested reply must be a separate string
    assert result["suggested_reply"] != original_email.strip(), \
        "suggested_reply must not equal the original email"
    assert len(result["suggested_reply"]) > 0, \
        "suggested_reply must not be empty"

    # Calling the function again with the suggested reply as input must NOT
    # produce the same title as the original email analysis
    reply_result = _demo_mode_analysis(result["suggested_reply"])
    assert reply_result["title"] != result["title"], (
        f"Analyzing the reply should produce a different title than analyzing the original. "
        f"Both produced: {result['title']!r}"
    )


# ── Test 14: Update Dashboard email extraction ────────────────────────────

def test_update_dashboard_email():
    text = (
        "Hi,\n\n"
        "Please update the dashboard before the next meeting. "
        "The metrics are outdated.\n\n"
        "Thanks,\nSarah"
    )
    result = _demo_mode_analysis(text)

    # Title: action-oriented, from original email
    assert "update" in result["title"].lower(), \
        f"Title should contain 'update', got: {result['title']!r}"
    assert "dashboard" in result["title"].lower(), \
        f"Title should contain 'dashboard', got: {result['title']!r}"

    # Deliverable: dashboard
    assert result["deliverable"] is not None, "Deliverable should be extracted"
    assert "dashboard" in result["deliverable"].lower(), \
        f"Deliverable should mention 'dashboard', got: {result['deliverable']!r}"

    # Deadline: 'before the next meeting' is not an explicit date
    assert_missing(result, "deadline")

    # Owner: not specified
    assert_missing(result, "owner")

    # Must ask about deadline
    questions = result["clarification_questions"]
    assert any(
        "deadline" in q.lower() or "date" in q.lower() or "meeting" in q.lower()
        for q in questions
    ), f"Expected deadline/meeting question, got: {questions}"

    # Description is the original email
    assert result["description"] == text.strip()
    text = (
        "Please complete the security audit report by October 31st.\n"
        "The report should follow ISO 27001 format."
    )
    result = _demo_mode_analysis(text)

    assert_missing(result, "owner")

    validation = check_missing_fields(result)
    assert "owner" in validation["missing_optional"], \
        f"owner should be in missing_optional: {validation}"


# ── Test 4: ASAP with no exact deadline ──────────────────────────────────────

def test_asap_no_deadline():
    text = "URGENT - Please handle the client complaint ASAP. The client is very unhappy."
    result = _demo_mode_analysis(text)

    assert_missing(result, "deadline")

    questions = result["clarification_questions"]
    urgency_q = any(
        "exact" in q.lower() or "deadline" in q.lower() or "date" in q.lower()
        for q in questions
    )
    assert urgency_q, f"Expected urgency-aware deadline question, got: {questions}"


# ── Test 5: Empty input ───────────────────────────────────────────────────────

def test_empty_input():
    result = _demo_mode_analysis("")
    assert result["title"] is None
    assert result["deadline"] is None
    assert result["deliverable"] is None
    assert result["_source"] == "demo"
    assert len(result["clarification_questions"]) > 0


# ── Test 6: Malformed AI response validation ──────────────────────────────────

def test_malformed_ai_response_validation():
    assert validate_ai_response({"title": "Something", "deadline": "Friday"}) is False
    assert validate_ai_response("not a dict") is False
    assert validate_ai_response(None) is False

    good = {
        "title": "Task", "description": "Do something", "deadline": "Friday",
        "owner": None, "deliverable": "Report", "missing_details": [],
        "clarification_questions": [], "suggested_reply": "OK"
    }
    assert validate_ai_response(good) is True


# ── Test 7: is_missing covers all placeholder strings ────────────────────────

def test_is_missing_placeholders():
    for val in [None, "", "null", "not specified", "see request",
                "assigned to recipient", "tbd", "N/A", "None"]:
        assert is_missing(val), f"Expected {val!r} to be treated as missing"

    for val in ["Friday", "Alex Johnson", "PDF report", "Backend team"]:
        assert not is_missing(val), f"Expected {val!r} to NOT be treated as missing"


# ── Test 15: AI JSON response validation ──────────────────────────────────────

def test_ai_response_validation():
    from services.ai_service import _validate_ai_json

    # Missing all keys
    assert _validate_ai_json({}) != []
    # Missing most keys
    assert _validate_ai_json({"task_title": "X"}) != []

    # Wrong type for list field
    bad = {
        "task_title": "T", "deadline": None, "deliverable": None,
        "description": "orig", "responsible_person": None,
        "missing_essential_fields": "not a list",
        "clarification_questions": [], "suggested_reply": "ok"
    }
    problems = _validate_ai_json(bad)
    assert any("missing_essential_fields" in p for p in problems)

    # Valid response
    good = {
        "task_title": "Prepare report", "deadline": "Friday",
        "deliverable": "PDF report", "description": "original email",
        "responsible_person": None, "missing_essential_fields": [],
        "clarification_questions": [], "suggested_reply": "Thanks"
    }
    assert _validate_ai_json(good) == []


# ── Test 16: _map_ai_response always uses original text as description ─────────

def test_map_ai_response_preserves_original():
    from services.ai_service import _map_ai_response

    original = "Hi, please update the dashboard."
    ai_json = {
        "task_title": "Update the dashboard",
        "deadline": None,
        "deliverable": "Updated dashboard",
        "description": "Thank you for your request...",  # model put reply here by mistake
        "responsible_person": None,
        "missing_essential_fields": ["deadline"],
        "clarification_questions": ["What is the deadline?"],
        "suggested_reply": "Thank you for your request..."
    }
    result = _map_ai_response(ai_json, original)

    # description must always be the original, never the model's description field
    assert result["description"] == original.strip()
    assert result["title"] == "Update the dashboard"
    assert result["owner"] is None
    assert result["_source"] == "ai"
    assert result["description"] != result["suggested_reply"]


# ── Test 17: analyze_with_ai falls back to demo when no key ───────────────────

def test_analyze_with_ai_falls_back_to_demo_without_key(monkeypatch):
    """With no API key, analyze_with_ai must return a demo result, not an error."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    from services.ai_service import analyze_with_ai
    result = analyze_with_ai("Please prepare the Q3 report by Friday.")
    assert result["_source"] == "demo", \
        f"Expected demo fallback, got _source={result['_source']!r}"
    assert result.get("title") is not None


# ── Test 18: analyze_with_ai returns error on auth failure (mocked) ────────────

def test_analyze_with_ai_returns_error_on_auth_failure(monkeypatch):
    """A bad API key must return _source='error' with a helpful message."""
    import pytest
    import services.ai_service as svc

    monkeypatch.setattr(svc, "_get_api_key", lambda: "sk-fake-key-for-testing")

    class FakeAuthError(Exception):
        pass

    class FakeCompletions:
        def create(self, **kwargs):
            raise FakeAuthError("401 authentication error: invalid api_key")

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    try:
        import openai
        monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: FakeClient())
    except ImportError:
        pytest.skip("openai package not installed")

    result = svc.analyze_with_ai("Please prepare the Q3 report.")
    assert result["_source"] == "error"
    assert "key" in result["_error"].lower() or "api" in result["_error"].lower()


# ── Test 19: _strip_json_fences removes markdown code blocks ──────────────────

def test_strip_json_fences():
    from services.ai_service import _strip_json_fences

    assert _strip_json_fences('```json\n{"task_title": "Test"}\n```') == '{"task_title": "Test"}'
    assert _strip_json_fences('{"task_title": "Test"}') == '{"task_title": "Test"}'
    assert _strip_json_fences('```\n{"task_title": "Test"}\n```') == '{"task_title": "Test"}'
