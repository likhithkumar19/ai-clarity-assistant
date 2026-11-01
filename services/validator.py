"""
validator.py
------------
Deterministic Python rules to check extracted task fields.
No AI involved here — pure logic checks.
"""

REQUIRED_FIELDS = ["title", "description", "deadline", "deliverable"]
OPTIONAL_FIELDS = ["owner"]

MISSING_INDICATORS = [None, "", "null", "not specified", "unknown", "n/a", "none",
                      "see request", "assigned to recipient", "not mentioned", "tbd"]


def is_missing(value) -> bool:
    """Return True if a value is considered missing or unknown."""
    if value is None:
        return True
    return str(value).strip().lower() in MISSING_INDICATORS


def check_missing_fields(extracted: dict) -> dict:
    """
    Check which required and optional fields are missing.
    Returns a dict with:
      - missing_required: list of missing required field names
      - missing_optional: list of missing optional field names
      - needs_clarification: True if any required field is missing
      - reasons: explanation for each missing field
    """
    missing_required = []
    missing_optional = []
    reasons = {}

    field_reasons = {
        "title": "A task title is needed to identify and track this request.",
        "description": "A clear description is needed to understand what work is required.",
        "deadline": "A deadline is needed to prioritize and schedule the task.",
        "deliverable": "The expected output or deliverable must be defined to confirm completion.",
        "owner": "Knowing who is responsible helps with accountability and follow-up.",
    }

    for field in REQUIRED_FIELDS:
        if is_missing(extracted.get(field)):
            missing_required.append(field)
            reasons[field] = field_reasons.get(field, "This field is required.")

    for field in OPTIONAL_FIELDS:
        if is_missing(extracted.get(field)):
            missing_optional.append(field)
            reasons[field] = field_reasons.get(field, "This field is optional but helpful.")

    return {
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "needs_clarification": len(missing_required) > 0,
        "reasons": reasons
    }


def validate_ai_response(response: dict) -> bool:
    """
    Validate that the AI response contains the expected schema.
    Returns True if valid, False otherwise.
    """
    expected_keys = [
        "title", "description", "deadline",
        "owner", "deliverable", "missing_details",
        "clarification_questions", "suggested_reply"
    ]
    if not isinstance(response, dict):
        return False
    for key in expected_keys:
        if key not in response:
            return False
    return True


def generate_clarification_questions(missing_fields: list) -> list:
    """
    Generate standard clarification questions for missing fields.
    These are deterministic — not AI generated.
    """
    question_map = {
        "title": "Could you provide a short title or name for this task?",
        "description": "Could you describe in more detail what needs to be done?",
        "deadline": "What is the expected deadline or due date for this task?",
        "deliverable": "What is the expected output or deliverable when this task is complete?",
        "owner": "Who is responsible for completing this task?",
    }
    return [question_map[f] for f in missing_fields if f in question_map]
