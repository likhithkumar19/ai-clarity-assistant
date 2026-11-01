"""
ai_service.py
-------------
Handles communication with the LLM API.
Falls back to demo mode if no API key is configured.
Demo mode uses deterministic sample responses — not real AI.
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Required JSON keys the model must return
_AI_REQUIRED_KEYS = [
    "task_title", "deadline", "deliverable", "description",
    "responsible_person", "missing_essential_fields",
    "clarification_questions", "suggested_reply"
]

SYSTEM_PROMPT = """
You are a workplace request analyzer. Extract structured information from the given email or task request.

Return ONLY a valid JSON object with EXACTLY these keys:
{
  "task_title": "concise action-oriented title, e.g. Prepare Q3 report — or null",
  "deadline": "exact date and time if stated, e.g. 28 October 2026, 4:00 PM — or null",
  "deliverable": "the expected output, e.g. PDF report — or null",
  "description": "the original request text, copied verbatim — never the suggested reply",
  "responsible_person": "named person or team if explicitly stated — or null",
  "missing_essential_fields": ["list of essential fields that are missing or ambiguous"],
  "clarification_questions": ["concise professional questions about missing information"],
  "suggested_reply": "a professional editable draft reply asking for the missing information"
}

Strict rules:
- Copy the original request verbatim into description. Never put the suggested reply there.
- Do NOT invent dates, names, deadlines, or requirements that are not in the request.
- Use null for any field that cannot be determined from the request.
- Treat 'ASAP' and 'as soon as possible' as urgency indicators, not exact deadlines — set deadline to null.
- If the request is fully clear, return empty lists for missing_essential_fields and clarification_questions.
- Return raw JSON only. No markdown fences, no explanation text.
"""


def _get_api_key() -> str:
    """Read API key from environment or Streamlit secrets. Never hardcode."""
    # 1. Environment variable / .env file
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key and key != "your_openai_api_key_here":
        return key
    # 2. Streamlit secrets (available when deployed on Streamlit Cloud)
    try:
        import streamlit as st
        key = st.secrets.get("OPENAI_API_KEY", "").strip()
        if key and key != "your_openai_api_key_here":
            return key
    except Exception:
        pass
    return ""


def _strip_json_fences(raw: str) -> str:
    """Remove markdown code fences that some models wrap around JSON."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        # Drop first line (```json or ```) and last line (```)
        inner = lines[1:] if lines[-1].strip() == "```" else lines[1:]
        raw = "\n".join(inner).strip().rstrip("`").strip()
    return raw


def _map_ai_response(raw_result: dict, original_text: str) -> dict:
    """
    Map the AI JSON response (new field names) to the internal schema
    (legacy field names used by the rest of the app and validator).
    Also enforces that description == original request, never the reply.
    """
    return {
        "title":                  raw_result.get("task_title"),
        "description":            original_text.strip(),   # always the original email
        "deadline":               raw_result.get("deadline"),
        "owner":                  raw_result.get("responsible_person"),
        "deliverable":            raw_result.get("deliverable"),
        "missing_details":        raw_result.get("missing_essential_fields", []),
        "clarification_questions": raw_result.get("clarification_questions", []),
        "suggested_reply":        raw_result.get("suggested_reply", ""),
        "_source":                "ai",
    }


def _validate_ai_json(data: dict) -> list[str]:
    """
    Return a list of problems with the AI JSON response.
    Empty list means the response is acceptable.
    """
    problems = []
    if not isinstance(data, dict):
        return ["Response is not a JSON object"]
    for key in _AI_REQUIRED_KEYS:
        if key not in data:
            problems.append(f"Missing key: {key}")
    for list_key in ("missing_essential_fields", "clarification_questions"):
        if list_key in data and not isinstance(data[list_key], list):
            problems.append(f"{list_key} must be a list")
    return problems


def analyze_with_ai(request_text: str) -> dict:
    """
    Analyze a request using the configured LLM.
    Falls back to demo mode when no API key is configured.
    Never overwrites the original request with the suggested reply.
    """
    api_key = _get_api_key()
    if not api_key:
        return _demo_mode_analysis(request_text)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"Analyze this request:\n\n{request_text}"}
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        raw = _strip_json_fences(response.choices[0].message.content)
        data = json.loads(raw)

        problems = _validate_ai_json(data)
        if problems:
            return {
                "_error": f"AI response was missing required fields: {', '.join(problems)}",
                "_source": "error"
            }

        return _map_ai_response(data, request_text)

    except json.JSONDecodeError as e:
        return {"_error": f"AI returned invalid JSON: {e}", "_source": "error"}
    except Exception as e:
        msg = str(e)
        if "api_key" in msg.lower() or "authentication" in msg.lower() or "401" in msg:
            return {"_error": "Invalid API key. Check OPENAI_API_KEY in your .env file.", "_source": "error"}
        if "rate" in msg.lower() or "429" in msg:
            return {"_error": "Rate limit reached. Please wait a moment and try again.", "_source": "error"}
        if "connect" in msg.lower() or "network" in msg.lower() or "timeout" in msg.lower():
            return {"_error": "Network error. Check your internet connection.", "_source": "error"}
        return {"_error": f"API error: {msg[:120]}", "_source": "error"}


# Words that indicate urgency but are NOT explicit deadlines
_URGENCY_WORDS = ["asap", "as soon as possible", "urgent", "urgently", "immediately", "right away"]

# Explicit deadline indicators (must not overlap with urgency words)
_DEADLINE_WORDS = ["by ", "due ", "due:", "deadline", "friday", "monday", "tuesday",
                   "wednesday", "thursday", "saturday", "sunday", "tomorrow",
                   "next week", "eod", "end of day", "end of week", "end of month",
                   "by end", "no later than", "jan ", "feb ", "mar ", "apr ", "may ",
                   "jun ", "jul ", "aug ", "sep ", "oct ", "nov ", "dec "]

# Deliverable noun phrases to extract
_DELIVERABLE_WORDS = {
    "report": "report", "document": "document", "presentation": "presentation",
    "spreadsheet": "spreadsheet", "summary": "summary", "analysis": "analysis",
    "proposal": "proposal", "plan": "plan", "file": "file", "draft": "draft",
    "review": "review document", "slide": "slide deck", "dashboard": "dashboard",
    "email": "email", "memo": "memo", "invoice": "invoice",
}


def _parse_email(text: str) -> tuple[str | None, str]:
    """
    Split raw text into (subject, body).
    Subject is the value after 'Subject:' on its own line, or None.
    Body has the subject line removed and greeting prefixes stripped.
    """
    import re
    lines = [l.strip() for l in text.strip().splitlines()]
    subject = None
    body_lines = []
    _GREETING_RE = re.compile(
        r'^(hi[,\s]|hello[,\s]|dear\s|hey[,\s])\s*\w*[,.]?\s*',
        re.IGNORECASE
    )
    for line in lines:
        if line.lower().startswith("subject:"):
            subject = line[len("subject:"):].strip()
            continue  # drop subject line entirely
        # Strip greeting prefix but keep the rest of the line
        stripped = _GREETING_RE.sub("", line).strip()
        if stripped:
            body_lines.append(stripped)
    body = " ".join(body_lines).strip()
    return subject, body


def _extract_title(text: str) -> str:
    """
    Build a concise action-oriented title from the first imperative clause.
    Only matches action verbs at the start of a sentence or after a filler opener.
    """
    import re
    subject, body = _parse_email(text)

    # Split body into sentences so we only look at sentence-initial verbs
    sentences = re.split(r'(?<=[.!?])\s+', body)

    # Pattern: optional filler + action verb + noun phrase up to a boundary
    action_pattern = re.compile(
        r'^(?:please\s+|kindly\s+|could you\s+|can you\s+)?'
        r'((?:prepare|create|write|complete|send|share|submit|review|update|fix|build|develop|deliver|draft|compile|finalize)'
        r'\s+[^,.;\n]+?)'  # noun phrase after verb
        r'(?=\s+using\b|\s+by\b|\s+before\b|\s+and\b|\s+as\s+soon|[,.]|$)',
        re.IGNORECASE
    )

    for sentence in sentences:
        m = action_pattern.match(sentence.strip())
        if m:
            title = m.group(1).strip()
            # Cap at 80 chars, break at last word boundary
            if len(title) > 80:
                title = title[:80].rsplit(" ", 1)[0]
            return title[0].upper() + title[1:]

    # Fall back to subject
    if subject:
        return subject[:80]

    # Last resort: first sentence stripped of filler opener
    first = sentences[0].split(".")[0].strip() if sentences else ""
    for filler in ["please ", "could you ", "can you ", "i need you to ", "kindly "]:
        if first.lower().startswith(filler):
            first = first[len(filler):].strip()
            break
    return (first[:80] if first else "Work Request")


def _extract_deliverable(text: str) -> str | None:
    """
    Extract the deliverable noun phrase from the body.
    Appends output format (PDF, Word, Excel, etc.) if explicitly stated.
    Stops at prepositions and conjunctions.
    """
    import re
    _, body = _parse_email(text)
    body_lower = body.lower()

    for keyword in _DELIVERABLE_WORDS:
        if keyword not in body_lower:
            continue
        # Noun phrase: optional article + up to 3 modifiers + keyword
        # Hard stop at prepositions/conjunctions
        pattern = re.compile(
            r'(?:the\s+|a\s+|an\s+)?(?:\w+\s+){0,3}' + re.escape(keyword)
            + r'(?=\s+(?:using|with|by|before|and|as|to|for|in|on|save|share|send)\b|[,.]|$)',
            re.IGNORECASE
        )
        match = pattern.search(body)
        if match:
            phrase = match.group(0).strip(" .,;:")
            # Remove leading action verbs
            for filler in ["please ", "prepare ", "create ", "write ", "complete ",
                           "send ", "share ", "submit ", "include ", "save "]:
                if phrase.lower().startswith(filler):
                    phrase = phrase[len(filler):].strip()
                    break
            # Strip leading article
            if re.match(r'^(the|a|an)\s+', phrase, re.IGNORECASE):
                phrase = re.sub(r'^(the|a|an)\s+', '', phrase, flags=re.IGNORECASE).strip()
            if not phrase:
                phrase = _DELIVERABLE_WORDS[keyword]
        else:
            phrase = _DELIVERABLE_WORDS[keyword]

        # Detect explicit output format: "save as a PDF", "in Word format", "as an Excel file"
        _FORMAT_PAT = re.compile(
            r'(?:save(?:\s+\w+){0,3}\s+as\s+(?:a\s+|an\s+)?|in\s+|as\s+(?:a\s+|an\s+)?)'
            r'(pdf|word|excel|powerpoint|pptx|xlsx|docx|csv|html|png|jpeg|jpg|zip)',
            re.IGNORECASE
        )
        fmt_m = _FORMAT_PAT.search(body)
        if fmt_m:
            fmt = fmt_m.group(1).upper()
            phrase = f"{phrase[0].upper() + phrase[1:]} in {fmt} format"
        else:
            phrase = phrase[0].upper() + phrase[1:]

        return phrase
    return None


def _extract_deadline(text_lower: str) -> str | None:
    """
    Return the matched deadline phrase, or None if only urgency words are present.
    Captures time + full date including month name and year.
    """
    import re
    scrubbed = text_lower
    for uw in _URGENCY_WORDS:
        scrubbed = scrubbed.replace(uw, "")

    # Try a rich date pattern first covering common formats:
    # "by 4:00 PM on 28 October 2026", "by October 28, 2026", "by Friday 5pm", etc.
    _MONTHS = (
        r'(?:january|february|march|april|may|june|july|august|'
        r'september|october|november|december)'
    )
    rich_pattern = re.compile(
        r'(?:by|due|before|no later than)\s+'
        r'(?:'
        # time + "on" + date: "4:00 PM on 28 October 2026"
        r'(?:\d{1,2}:\d{2}\s*(?:am|pm)?\s+on\s+)?'
        r'(?:'
        # day-first: "28 October 2026" or "28th October 2026"
        r'\d{1,2}(?:st|nd|rd|th)?\s+' + _MONTHS + r'(?:,?\s+\d{4})?'
        r'|'
        # month-first: "October 28, 2026" or "October 28 2026"
        + _MONTHS + r'\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?'
        r'|'
        # numeric: "28/10/2026" or "10-28-2026"
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
        r'|'
        # weekday with optional time: "Friday 5pm"
        r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
        r'(?:\s+\d{1,2}:\d{2}\s*(?:am|pm)?|\s+\d{1,2}\s*(?:am|pm))?'
        r'|eod|end of day|end of week|end of month|next week|tomorrow'
        r')'
        r')',
        re.IGNORECASE
    )
    m = rich_pattern.search(scrubbed)
    if m:
        return m.group(0).strip(" .,;:")

    # Fall back: trigger word + up to 8 tokens, stop at sentence-ending punctuation
    for dw in _DEADLINE_WORDS:
        if dw not in scrubbed:
            continue
        pattern = re.compile(
            re.escape(dw.strip())
            + r'(?:\s+[\w:]+){0,8}',
            re.IGNORECASE
        )
        match = pattern.search(scrubbed)
        if match:
            # Trim at first full-stop or newline equivalent in the phrase
            phrase = match.group(0).split(".")[0].strip(" .,;:")
            return phrase if phrase else dw.strip()
        return dw.strip()
    return None


def _normalize_deadline(raw: str) -> str:
    """
    Normalize a raw extracted deadline string into a readable format.
    Examples:
      "by 4:00 pm on 28 october 2026"  -> "28 October 2026, 4:00 PM"
      "by friday 5pm"                  -> "Friday, 5:00 PM"
      "by october 28, 2026"            -> "28 October 2026"
      "eod"                            -> "End of Day"
    Does not invent missing parts.
    """
    import re

    s = raw.strip().lower()
    # Strip leading trigger words
    s = re.sub(r'^(by|due|before|no later than)\s+', '', s).strip()

    _MONTH_MAP = {
        "january": "January", "february": "February", "march": "March",
        "april": "April", "may": "May", "june": "June",
        "july": "July", "august": "August", "september": "September",
        "october": "October", "november": "November", "december": "December",
    }
    _MONTH_PAT = r'(?:' + '|'.join(_MONTH_MAP.keys()) + r')'
    _DAY_PAT   = r'\d{1,2}(?:st|nd|rd|th)?'
    _YEAR_PAT  = r'\d{4}'
    _TIME_PAT  = r'\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm)'

    # Extract time if present
    time_m = re.search(_TIME_PAT, s, re.IGNORECASE)
    time_str = None
    if time_m:
        t = time_m.group(0).strip()
        # Normalise to HH:MM AM/PM
        t_clean = re.sub(r'\s+', '', t).upper()
        hm = re.match(r'(\d{1,2}):(\d{2})(AM|PM)?', t_clean)
        if hm:
            h, m_part, ampm = hm.group(1), hm.group(2), hm.group(3) or ""
            time_str = f"{int(h):02d}:{m_part} {ampm}".strip() if ampm else f"{int(h):02d}:{m_part}"
        else:
            # e.g. "5pm" -> "5:00 PM"
            honly = re.match(r'(\d{1,2})(AM|PM)', t_clean)
            if honly:
                time_str = f"{int(honly.group(1))}:00 {honly.group(2)}"
        # Remove time portion from s for date parsing
        s = s[:time_m.start()] + s[time_m.end():]
        s = re.sub(r'\bon\b', '', s).strip()

    # Extract year
    year_m = re.search(_YEAR_PAT, s)
    year_str = year_m.group(0) if year_m else None
    if year_m:
        s = s[:year_m.start()] + s[year_m.end():]

    # Extract month
    month_m = re.search(_MONTH_PAT, s, re.IGNORECASE)
    month_str = _MONTH_MAP[month_m.group(0).lower()] if month_m else None
    if month_m:
        s = s[:month_m.start()] + s[month_m.end():]

    # Extract day number
    day_m = re.search(_DAY_PAT, s)
    day_str = re.sub(r'(st|nd|rd|th)$', '', day_m.group(0)) if day_m else None

    # Weekday-only (no numeric date)
    _DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    weekday_m = re.search(r'\b(' + '|'.join(_DAYS) + r')\b', raw.lower())

    # Assemble
    if month_str and day_str:
        date_part = f"{day_str} {month_str}"
        if year_str:
            date_part += f" {year_str}"
        return f"{date_part}, {time_str}" if time_str else date_part
    elif weekday_m:
        day_name = weekday_m.group(1).capitalize()
        return f"{day_name}, {time_str}" if time_str else day_name
    elif time_str:
        return time_str
    # Named shortcuts
    shortcuts = {"eod": "End of Day", "end of day": "End of Day",
                 "end of week": "End of Week", "end of month": "End of Month",
                 "next week": "Next Week", "tomorrow": "Tomorrow"}
    for k, v in shortcuts.items():
        if k in raw.lower():
            return v
    # Fall back: title-case the raw string with trigger word stripped
    return re.sub(r'^(by|due|before|no later than)\s+', '', raw, flags=re.IGNORECASE).strip().title()


def _has_explicit_owner(text: str) -> bool:
    """
    Return True only when a named person or specific team is identified as owner.
    Pronouns like 'you' or 'please' do NOT count.
    """
    import re
    text_lower = text.lower()
    owner_patterns = [
        r"owner\s*:\s*\w+",
        r"assigned to\s+[A-Z][a-z]+",
        r"responsible\s*:\s*\w+",
        r"lead\s*:\s*\w+",
    ]
    for pattern in owner_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    team_keywords = ["dev team", "backend team", "frontend team", "design team",
                     "qa team", "finance team", "hr team", "it team", "ops team"]
    return any(kw in text_lower for kw in team_keywords)


def _demo_mode_analysis(request_text: str) -> dict:
    """
    Demo mode: deterministic analysis without AI.
    Clearly labelled as demo — not real AI output.
    """
    text_lower = request_text.lower().strip()

    # Empty input
    if not text_lower:
        return {
            "title": None,
            "description": None,
            "deadline": None,
            "owner": None,
            "deliverable": None,
            "missing_details": ["No request text provided"],
            "clarification_questions": ["Could you please provide the request details?"],
            "suggested_reply": "Could you please share the details of your request?",
            "_source": "demo"
        }

    deadline_value = _extract_deadline(text_lower)
    if deadline_value is not None:
        deadline_value = _normalize_deadline(deadline_value)
    has_explicit_deadline = deadline_value is not None
    is_urgent = any(uw in text_lower for uw in _URGENCY_WORDS)
    deliverable = _extract_deliverable(request_text)
    has_owner = _has_explicit_owner(request_text)

    missing = []
    questions = []

    if not has_explicit_deadline:
        missing.append("No explicit deadline mentioned")
        if is_urgent:
            questions.append("The request mentions urgency but no specific date — what is the exact deadline?")
        else:
            questions.append("What is the expected deadline or due date for this task?")

    if not deliverable:
        missing.append("Expected deliverable is unclear")
        questions.append("What is the expected output or deliverable when this task is complete?")
    else:
        # Deliverable exists but scope may be vague
        vague_scope_words = ["important details", "all details", "everything", "relevant info", "as discussed"]
        if any(v in text_lower for v in vague_scope_words):
            missing.append("Deliverable scope is ambiguous")
            # Strip leading article from deliverable to avoid "the The project report"
            deliverable_phrase = deliverable.lstrip()
            if deliverable_phrase.lower().startswith(("the ", "a ", "an ")):
                deliverable_phrase = deliverable_phrase.split(" ", 1)[1]
            questions.append(f"What specific sections or content should the {deliverable_phrase} include?")

    # Owner is always optional — only add to questions when other essentials are missing
    # (a request with clear task + deliverable + deadline does not need owner to proceed)
    essentials_present = has_explicit_deadline and deliverable
    if not has_owner:
        if not essentials_present:
            # Essentials are missing too — owner question is part of the required clarification
            missing.append("Responsible person not confirmed")
            questions.append("Could you confirm who is responsible for completing this task?")
        # When essentials are present, owner absence is recorded in missing_details only
        # so the validator can surface it as optional — no question generated

    title = _extract_title(request_text)
    description = request_text.strip()  # preserve full original text, no truncation

    suggested_reply = ""
    if questions:
        q_list = "\n".join(f"- {q}" for q in questions)
        suggested_reply = (
            f"Thank you for your request. To ensure I can complete this accurately, "
            f"I have a few clarifying questions:\n\n{q_list}\n\n"
            f"Please let me know at your earliest convenience.\n\nBest regards"
        )
    else:
        suggested_reply = (
            "Thank you for your clear request. I have all the information needed "
            "and will proceed accordingly.\n\nBest regards"
        )

    return {
        "title": title,
        "description": description,
        "deadline": deadline_value,
        "owner": None if not has_owner else "Confirmed in request",
        "deliverable": deliverable,
        "missing_details": missing,
        "clarification_questions": questions,
        "suggested_reply": suggested_reply,
        "_source": "demo"
    }
