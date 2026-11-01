"""
app.py
------
AI Work Request Clarity Assistant
Main Streamlit application entry point.
"""

import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(__file__))

from services.database import init_db, save_task, get_all_tasks, update_task_status, get_task_counts
from services.ai_service import analyze_with_ai
from services.validator import check_missing_fields, validate_ai_response
from data.sample_requests import SAMPLE_REQUESTS

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Clarity Assistant",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ── Initialize DB ─────────────────────────────────────────────────────────────
init_db()

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Global font */
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }

    /* Page background */
    .stApp { background-color: #f4f6f9; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #1f2937; }
    section[data-testid="stSidebar"] * { color: #f9fafb !important; }
    section[data-testid="stSidebar"] .stRadio label { font-size: 15px; }

    /* Main title */
    .main-title {
        font-size: 1.8rem; font-weight: 700;
        color: #1f2937; margin-bottom: 2px;
    }
    .sub-title { font-size: 0.95rem; color: #6b7280; margin-bottom: 1.2rem; }

    /* Badges */
    .demo-badge {
        background: #fffbeb; color: #b45309; padding: 5px 12px;
        border-radius: 6px; font-size: 13px; font-weight: 600;
        border: 1px solid #fcd34d; display: inline-block; margin-bottom: 12px;
    }
    .ai-badge {
        background: #ecfdf5; color: #065f46; padding: 5px 12px;
        border-radius: 6px; font-size: 13px; font-weight: 600;
        border: 1px solid #6ee7b7; display: inline-block; margin-bottom: 12px;
    }

    /* Field cards */
    .field-card {
        background: #ffffff; border: 1px solid #e5e7eb;
        border-radius: 8px; padding: 12px 16px; margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .field-card strong { color: #374151; font-size: 13px; }

    /* Warnings & success */
    .missing-warning {
        background: #fff1f2; border-left: 4px solid #f87171;
        border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;
        color: #b91c1c; font-size: 14px;
    }
    .success-box {
        background: #f0fdf4; border-left: 4px solid #4ade80;
        border-radius: 6px; padding: 10px 14px; color: #15803d; font-size: 14px;
    }

    /* Stat cards */
    .stat-card {
        background: #ffffff; border: 1px solid #e5e7eb;
        border-radius: 10px; padding: 18px 10px; text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .stat-number { font-size: 1.8rem; font-weight: 700; }
    .stat-label { font-size: 12px; color: #6b7280; margin-top: 4px; }

    /* Buttons */
    .stButton > button {
        border-radius: 6px; font-weight: 600; font-size: 14px;
        padding: 6px 18px;
    }

    /* Inputs */
    .stTextInput > div > input, .stTextArea > div > textarea {
        border-radius: 6px; border: 1px solid #d1d5db;
        font-size: 14px;
    }

    /* Divider */
    hr { border-color: #e5e7eb; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 AI Clarity Assistant")
    st.markdown("---")
    page = st.radio(
        "Navigation",
        ["📝 Analyze Request", "📋 Task Dashboard"],
        label_visibility="visible"
    )
    st.markdown("---")

    from services.ai_service import _get_api_key
    api_key = _get_api_key()
    if api_key:
        st.success("🔑 API key detected")
        mode = st.radio("Analysis mode", ["🤖 Real AI", "🔶 Demo Mode"], index=0, key="mode")
    else:
        st.warning("⚠️ No API key found. Running in Demo Mode.")
        st.caption("Add OPENAI_API_KEY to .env to enable real AI.")
        mode = "🔶 Demo Mode"
        st.session_state["mode"] = mode

    st.markdown("---")
    st.caption("Accenture AI Challenge 2024")
    st.caption("Built with Streamlit + OpenAI")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — ANALYZE REQUEST
# ══════════════════════════════════════════════════════════════════════════════
if "📝 Analyze Request" in page:

    st.markdown('<p class="main-title">🤖 AI Work Request Clarity Assistant</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Paste a workplace email or task request. The AI will extract key details, flag missing info, and suggest clarification questions.</p>', unsafe_allow_html=True)
    st.divider()

    # ── Sample request loader ─────────────────────────────────────────────────
    with st.expander("📂 Load a Sample Request for Testing", expanded=False):
        sample_labels = [s["label"] for s in SAMPLE_REQUESTS]
        selected_label = st.selectbox("Choose a sample:", sample_labels, key="sample_select")
        selected_sample = next(s for s in SAMPLE_REQUESTS if s["label"] == selected_label)
        st.caption(f"**Expected result:** {selected_sample['expected']}")
        if st.button("Load This Sample", key="load_sample"):
            st.session_state["request_text"] = selected_sample["text"]
            st.rerun()

    # ── Request input ─────────────────────────────────────────────────────────
    request_text = st.text_area(
        "📧 Paste your email or task request here:",
        value=st.session_state.get("request_text", ""),
        height=200,
        placeholder="e.g. Hi, can you please prepare the Q3 report by Friday? We need it in PDF format...",
        key="request_input"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        analyze_btn = st.button("🔍 Analyze Request", type="primary", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear", use_container_width=False):
            st.session_state["request_text"] = ""
            if "analysis" in st.session_state:
                del st.session_state["analysis"]
            if "original_request" in st.session_state:
                del st.session_state["original_request"]
            st.rerun()

    # ── Validation ────────────────────────────────────────────────────────────
    if analyze_btn:
        if not request_text or not request_text.strip():
            st.error("⚠️ Please enter a request before analyzing.")
        else:
            with st.spinner("Analyzing your request..."):
                selected_mode = st.session_state.get("mode", "🔶 Demo Mode")
                if "Demo" in selected_mode:
                    from services.ai_service import _demo_mode_analysis
                    result = _demo_mode_analysis(request_text)
                else:
                    result = analyze_with_ai(request_text)
                st.session_state["analysis"] = result
                # Store original email separately — never overwritten by reply
                st.session_state["original_request"] = request_text
                st.session_state["request_text"] = request_text

    # ── Display analysis results ──────────────────────────────────────────────
    if "analysis" in st.session_state:
        result = st.session_state["analysis"]

        # Handle errors
        if result.get("_source") == "error":
            st.error(f"❌ {result.get('_error', 'An unknown error occurred.')}")
            st.stop()

        # Source badge
        source = result.get("_source")
        if source == "ai":
            st.markdown('<span class="ai-badge">✅ REAL AI MODE — OpenAI analysis</span>', unsafe_allow_html=True)
        elif source == "demo":
            st.markdown('<span class="demo-badge">🔶 DEMO MODE — Not real AI output</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="demo-badge">🔶 DEMO MODE — Not real AI output</span>', unsafe_allow_html=True)

        st.markdown("---")

        # ── Extracted fields ──────────────────────────────────────────────────
        st.markdown("### 📊 Extracted Information")
        col1, col2 = st.columns(2)

        fields = {
            "📌 Task Title": result.get("title"),
            "📝 Description": result.get("description"),
            "📅 Deadline": result.get("deadline"),
            "👤 Responsible Person": result.get("owner"),
            "📦 Deliverable": result.get("deliverable"),
        }

        items = list(fields.items())
        for i, (label, value) in enumerate(items):
            col = col1 if i % 2 == 0 else col2
            with col:
                display_val = value if value and str(value).lower() not in ["null", "none", "not specified", ""] else "⚠️ Not specified"
                color = "#dc2626" if "⚠️" in display_val else "#1e293b"
                st.markdown(f"""
                <div class="field-card">
                    <strong>{label}</strong><br>
                    <span style="color:{color}">{display_val}</span>
                </div>
                """, unsafe_allow_html=True)

        # ── Missing info checker ──────────────────────────────────────────────
        validation = check_missing_fields(result)

        st.markdown("### 🔍 Clarity Check")
        if not validation["needs_clarification"]:
            st.markdown('<div class="success-box">✅ This request is sufficiently clear. No essential information is missing.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"**{len(validation['missing_required'])} essential field(s) missing:**")
            for field in validation["missing_required"]:
                reason = validation["reasons"].get(field, "")
                st.markdown(f"""
                <div class="missing-warning">
                    ❌ <strong>{field.replace('_', ' ').title()}</strong> — {reason}
                </div>
                """, unsafe_allow_html=True)

        if validation["missing_optional"]:
            with st.expander("ℹ️ Optional fields not specified"):
                for field in validation["missing_optional"]:
                    st.caption(f"• {field.replace('_', ' ').title()}: {validation['reasons'].get(field, '')}")

        # ── Clarification questions ───────────────────────────────────────────
        questions = result.get("clarification_questions", [])
        if questions:
            st.markdown("### ❓ Clarification Questions")
            for i, q in enumerate(questions, 1):
                st.markdown(f"**{i}.** {q}")

        # ── Suggested reply ───────────────────────────────────────────────────
        st.markdown("### 💬 Suggested Reply")
        suggested = result.get("suggested_reply", "")
        edited_reply = st.text_area(
            "Edit the reply before copying:",
            value=suggested,
            height=150,
            key="edited_reply"
        )
        st.caption("✏️ You can edit this reply. It will NOT be sent automatically.")

        # ── Task confirmation ─────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### ✅ Confirm & Save Task")
        st.caption("Review and correct the details below before saving.")

        # Use the original email as description — never the suggested reply
        original_request = st.session_state.get("original_request", result.get("description", ""))

        with st.form("confirm_task_form"):
            c1, c2 = st.columns(2)
            with c1:
                task_title = st.text_input("Task Title *", value=result.get("title") or "")
                task_deadline = st.text_input("Deadline", value=result.get("deadline") or "Not specified")
            with c2:
                task_owner = st.text_input("Responsible Person", value=result.get("owner") or "Not specified")
                task_deliverable = st.text_input("Deliverable", value=result.get("deliverable") or "Not specified")

            task_description = st.text_area("Description", value=original_request, height=100)

            submitted = st.form_submit_button("💾 Save Task", type="primary")

            if submitted:
                if not task_title.strip():
                    st.error("Task title is required before saving.")
                else:
                    task_data = {
                        "title": task_title,
                        "description": task_description,
                        "deadline": task_deadline,
                        "owner": task_owner,
                        "deliverable": task_deliverable,
                        "missing_info": ", ".join(validation["missing_required"]),
                        "clarification_questions": "\n".join(questions),
                        "needs_clarification": validation["needs_clarification"]
                    }
                    task_id = save_task(task_data)
                    st.success(f"✅ Task saved successfully! Task ID: **{task_id}**")
                    del st.session_state["analysis"]
                    if "original_request" in st.session_state:
                        del st.session_state["original_request"]
                    st.balloons()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — TASK DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif "📋 Task Dashboard" in page:

    st.markdown('<p class="main-title">📋 Task Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">View and manage all confirmed tasks.</p>', unsafe_allow_html=True)
    st.divider()

    # ── Stats ─────────────────────────────────────────────────────────────────
    counts = get_task_counts()
    c1, c2, c3, c4, c5 = st.columns(5)
    stats = [
        (c1, counts["total"], "Total Tasks", "#6366f1"),
        (c2, counts["pending"], "Pending", "#f59e0b"),
        (c3, counts["in_progress"], "In Progress", "#3b82f6"),
        (c4, counts["completed"], "Completed", "#10b981"),
        (c5, counts["needs_clarification"], "Need Clarification", "#ef4444"),
    ]
    for col, num, label, color in stats:
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number" style="color:{color}">{num}</div>
                <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Task list ─────────────────────────────────────────────────────────────
    tasks = get_all_tasks()

    if not tasks:
        st.info("📭 No tasks saved yet. Go to **Analyze Request** to create your first task.")
    else:
        # Filter
        status_filter = st.selectbox("Filter by status:", ["All", "Pending", "In Progress", "Completed"])
        filtered = tasks if status_filter == "All" else [t for t in tasks if t["status"] == status_filter]

        st.markdown(f"**Showing {len(filtered)} task(s)**")
        st.markdown("")

        for task in filtered:
            status_color = {"Pending": "#f59e0b", "In Progress": "#3b82f6", "Completed": "#10b981"}.get(task["status"], "#64748b")
            clarification_badge = "⚠️ Needs Clarification" if task["needs_clarification"] else "✅ Clear"

            with st.expander(f"**{task['id']}** — {task['title']} | {task['status']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📅 Deadline:** {task['deadline']}")
                    st.markdown(f"**👤 Owner:** {task['owner']}")
                    st.markdown(f"**📦 Deliverable:** {task['deliverable']}")
                with col2:
                    st.markdown(f"**🕐 Created:** {task['created_at']}")
                    st.markdown(f"**Clarity:** {clarification_badge}")
                    st.markdown(f"**Status:** <span style='color:{status_color};font-weight:600'>{task['status']}</span>", unsafe_allow_html=True)

                if task["description"]:
                    st.markdown(f"**📝 Description:** {task['description'][:200]}")

                if task["missing_info"]:
                    st.markdown(f"**❌ Missing:** {task['missing_info']}")

                # Status update
                new_status = st.selectbox(
                    "Update Status:",
                    ["Pending", "In Progress", "Completed"],
                    index=["Pending", "In Progress", "Completed"].index(task["status"]),
                    key=f"status_{task['id']}"
                )
                if st.button("Update", key=f"update_{task['id']}"):
                    update_task_status(task["id"], new_status)
                    st.success(f"Status updated to **{new_status}**")
                    st.rerun()
