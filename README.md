# AI Work Request Clarity Assistant

An AI-powered web application that analyzes workplace emails and task requests,
identifies missing information, generates clarification questions, and converts
reviewed requests into trackable tasks.

Built for the **Accenture AI Challenge**.

---

## Features

- Paste any workplace email or task request
- Real AI (OpenAI) or Demo Mode — switchable from the sidebar
- Extracts: task title, description, deadline, owner, deliverable
- Identifies missing or ambiguous information
- Generates professional clarification questions and editable reply
- Save confirmed tasks to SQLite database
- Task dashboard with status tracking
- Works in Demo Mode without an API key

---

## Project Structure

```
ai-clarity-assistant/
├── app.py                    # Main Streamlit application
├── services/
│   ├── ai_service.py         # LLM API + demo mode + validation
│   ├── validator.py          # Field validation rules
│   └── database.py           # SQLite operations
├── data/
│   └── sample_requests.py    # 15 fictional test requests
├── tests/
│   └── test_analysis.py      # Regression tests (run without API key)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Installation

### Step 1 — Install Python 3.10+
Download from https://python.org

### Step 2 — Clone or download the project
```cmd
d:
cd ai-clarity-assistant
```

### Step 3 — Install dependencies
```cmd
python -m pip install -r requirements.txt
```

### Step 4 — Configure API key (required for Real AI mode)
```cmd
copy .env.example .env
```
Edit `.env` and replace the placeholder:
```
OPENAI_API_KEY=sk-your-real-key-here
OPENAI_MODEL=gpt-3.5-turbo
```
If you skip this step, the app runs in **Demo Mode** automatically.

### Step 5 — Run the application
```cmd
python -m streamlit run app.py
```

Open your browser at: http://localhost:8501

---

## Modes

| Mode | Badge shown | Requires |
|------|-------------|----------|
| Real AI | ✅ REAL AI MODE | `OPENAI_API_KEY` in `.env` |
| Demo | 🔶 DEMO MODE | Nothing — always available |
| Error | ❌ error message | Shown on API/network failure |

Switch modes from the sidebar. Demo Mode uses deterministic rules and is
clearly labelled — it is **not** real AI output.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(none)* | OpenAI secret key |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | Model name (`gpt-4o` for better accuracy) |

Keys are read from `.env` or Streamlit Secrets. They are never hardcoded or logged.

---

## Running Tests

Tests run entirely in Demo Mode — no API key required.

```cmd
python -m pytest tests/ -v
```

---

## Security Notes

- Never commit your `.env` file (it is in `.gitignore`)
- API keys are read from environment variables or Streamlit Secrets only
- No email content is logged or stored externally
- No connection to Outlook, Teams, or any mail service
