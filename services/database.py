"""
database.py
-----------
Handles all SQLite operations.
Creates the database and tasks table automatically on first run.
"""

import sqlite3
import uuid
from datetime import datetime

DB_PATH = "tasks.db"


def init_db():
    """Create the tasks table if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            deadline TEXT,
            owner TEXT,
            deliverable TEXT,
            missing_info TEXT,
            clarification_questions TEXT,
            status TEXT DEFAULT 'Pending',
            needs_clarification INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_task(task: dict) -> str:
    """Save a confirmed task and return its ID."""
    task_id = str(uuid.uuid4())[:8].upper()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks
        (id, title, description, deadline, owner, deliverable,
         missing_info, clarification_questions, status, needs_clarification, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        task_id,
        task.get("title", "Untitled Task"),
        task.get("description", ""),
        task.get("deadline", "Not specified"),
        task.get("owner", "Not specified"),
        task.get("deliverable", "Not specified"),
        task.get("missing_info", ""),
        task.get("clarification_questions", ""),
        "Pending",
        1 if task.get("needs_clarification") else 0,
        now
    ))
    conn.commit()
    conn.close()
    return task_id


def get_all_tasks() -> list:
    """Return all tasks as a list of dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_task_status(task_id: str, new_status: str):
    """Update the status of a task."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
    conn.commit()
    conn.close()


def get_task_counts() -> dict:
    """Return counts by status and clarification need."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'In Progress'")
    in_progress = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Completed'")
    completed = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE needs_clarification = 1")
    needs_clarification = cursor.fetchone()[0]
    conn.close()
    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "completed": completed,
        "needs_clarification": needs_clarification
    }
