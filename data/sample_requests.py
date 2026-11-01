"""
sample_requests.py
------------------
15 fictional workplace email/task requests for testing.
All names, companies, and details are completely fictional.
"""

SAMPLE_REQUESTS = [
    {
        "id": 1,
        "label": "1. Missing deadline",
        "text": """Hi,

Can you please prepare a competitor analysis report for our Q3 strategy meeting?
We need to cover at least 5 competitors including their pricing, features, and market share.
The report should be in PowerPoint format.

Thanks,
Sarah Mitchell
Product Manager""",
        "expected": "Missing deadline — should ask when the report is needed."
    },
    {
        "id": 2,
        "label": "2. Unclear deliverable",
        "text": """Hello,

We need to do something about the onboarding process. It's been getting complaints.
Please look into it and get back to me.

Regards,
James Thornton
HR Director""",
        "expected": "Unclear deliverable — should ask what specific output is expected (report, new process, presentation?)."
    },
    {
        "id": 3,
        "label": "3. Multiple missing details",
        "text": """Hey,

Can you handle the client thing we discussed?

Thanks""",
        "expected": "Missing title, description, deadline, deliverable, and owner — almost everything is missing."
    },
    {
        "id": 4,
        "label": "4. Clear request — no clarification needed",
        "text": """Hi Alex,

Please prepare a 2-page executive summary of the Q2 sales performance report by Friday 5pm.
The summary should include total revenue, top 3 performing regions, and key recommendations.
Send the final document to me and copy in the finance team.

Deadline: Friday, 5:00 PM
Owner: Alex Johnson

Best regards,
Linda Carter
VP of Sales""",
        "expected": "Clear request — no clarification needed. All fields present."
    },
    {
        "id": 5,
        "label": "5. No explicit deadline",
        "text": """Hi Team,

We need to update the employee handbook to reflect the new remote work policy
that was approved last month. Please make sure all sections related to attendance,
leave, and communication tools are updated.

The updated handbook should be shared with all employees once complete.

Thanks,
Rachel Green
People Operations""",
        "expected": "No explicit deadline — should ask when this needs to be completed."
    },
    {
        "id": 6,
        "label": "6. Empty input",
        "text": "",
        "expected": "Empty input — should show validation error, not call AI."
    },
    {
        "id": 7,
        "label": "7. Missing responsible person",
        "text": """Dear Team,

The annual IT security audit needs to be completed before the end of this month.
Please ensure all systems are scanned, vulnerabilities are documented,
and a final audit report is submitted by October 31st.

The report should follow the ISO 27001 format.

IT Compliance Team""",
        "expected": "Missing owner — should ask who is responsible for completing the audit."
    },
    {
        "id": 8,
        "label": "8. Ambiguous scope",
        "text": """Hi,

Can you work on improving the website? We've had some feedback that it's not great.
Let me know when it's done.

Thanks,
Tom""",
        "expected": "Ambiguous scope — should ask what specific improvements are needed, deadline, and deliverable."
    },
    {
        "id": 9,
        "label": "9. Clear technical task",
        "text": """Hi Dev Team,

Please fix the login page bug where users are being logged out after 5 minutes
instead of the configured 30-minute session timeout.

Expected fix: Update the session configuration in auth_config.py to set
SESSION_TIMEOUT = 1800 seconds.

Priority: High
Deadline: Tomorrow EOD (End of Day)
Owner: Backend Development Team

Reported by: QA Team""",
        "expected": "Clear technical task — minimal clarification needed."
    },
    {
        "id": 10,
        "label": "10. Missing deliverable format",
        "text": """Hello,

Please conduct a customer satisfaction survey for our enterprise clients
who signed up in the last 6 months. The survey should cover product usability,
support quality, and overall satisfaction.

Complete this by November 15th.

Thanks,
Maria Santos
Customer Success Manager""",
        "expected": "Missing deliverable format — should ask what format the results should be in (report, spreadsheet, presentation?)."
    },
    {
        "id": 11,
        "label": "11. Conflicting information",
        "text": """Hi,

We need the budget proposal for next year ready by end of this week.
Actually, the board meeting is on Monday so we need it by Sunday night.
The proposal should cover all department budgets.

Let me know if you need anything.

David""",
        "expected": "Conflicting deadline — should clarify whether deadline is end of week or Sunday night."
    },
    {
        "id": 12,
        "label": "12. Multiple owners unclear",
        "text": """Team,

The product roadmap for 2025 needs to be finalized. Engineering, Design,
and Product teams should all contribute. We need this ready for the
all-hands meeting next Thursday.

Please coordinate and submit the final roadmap document.

Thanks,
CEO Office""",
        "expected": "Multiple owners — should ask who is the primary owner responsible for coordinating."
    },
    {
        "id": 13,
        "label": "13. Urgent but vague",
        "text": """URGENT - Please handle the client complaint ASAP.
The client is very unhappy. This needs to be resolved today.""",
        "expected": "Urgent but vague — missing client name, nature of complaint, and expected resolution."
    },
    {
        "id": 14,
        "label": "14. Well-structured project request",
        "text": """Hi Priya,

I would like you to lead the development of a new employee onboarding portal.

Deliverable: A working web application with the following features:
- New employee registration form
- Document upload functionality
- IT equipment request form
- First-week schedule display

Timeline: MVP to be completed by December 31st, 2024
Owner: Priya Sharma (Lead Developer)
Budget: Approved — see project code PRJ-2024-089

Please confirm receipt and share a project plan by next Friday.

Best regards,
Michael Brown
CTO""",
        "expected": "Well-structured request — all key fields present, minimal clarification needed."
    },
    {
        "id": 15,
        "label": "15. Request with no context",
        "text": """Hi,

Following up on our conversation. Please proceed as discussed.

Thanks""",
        "expected": "No context — almost everything is missing, needs full clarification."
    },
]
