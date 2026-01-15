# app/local_planner.py
import re
from typing import Dict, Any, List

GMAIL_INTENTS = {"sender_request"}  # genişletilebilir

def _extract_count(user_text: str, default: int = 4) -> int:
    # "son 4", "last 3" vb.
    m = re.search(r"\bson\s+(\d+)", user_text, flags=re.IGNORECASE)
    if m:
        return max(1, min(50, int(m.group(1))))
    m = re.search(r"\blast\s+(\d+)", user_text, flags=re.IGNORECASE)
    if m:
        return max(1, min(50, int(m.group(1))))
    return default

def plan(user_id: str, user_text: str, parsed_intent: str) -> Dict[str, Any]:
    """
    Deterministic local plan when LLM planning is unavailable or fails.
    Currently supports 'sender_request' for Gmail.
    """
    if parsed_intent not in GMAIL_INTENTS:
        raise ValueError("Local planner has no template for this intent")

    n = _extract_count(user_text, default=4)

    steps: List[Dict[str, Any]] = [
        {
            "id": "step_1",
            "title": "List last N Gmail messages",
            "description": "List ID/threadId of recent messages",
            "tool_name": "google_oauth2_manager",
            "action_name": "gmail_list_messages",
            "params": {"max_results": n, "label_ids": ["INBOX"]},
            "dependencies": [],
            "estimated_duration": 30,
            "validation": "messages.messages exists"
        },
        {
            "id": "step_2",
            "title": "Fetch details for each message",
            "description": "Get headers for each listed message",
            "tool_name": "google_oauth2_manager",
            "action_name": "gmail_get_message",
            "params": {"message_ids_from": "step_1", "format": "metadata"},
            "dependencies": ["step_1"],
            "estimated_duration": 60,
            "validation": "headers for each id"
        },
        {
            "id": "step_3",
            "title": "Extract senders",
            "description": "Extract 'From' header (name/email) and prepare final result",
            "tool_name": "__internal__",  # built-in aggregator
            "action_name": "aggregate_gmail_senders",
            "params": {"source_step": "step_2"},
            "dependencies": ["step_2"],
            "estimated_duration": 5,
            "validation": "list of senders length == N"
        }
    ]

    return {
        "title": "Local Gmail Sender Listing",
        "description": "Deterministic local workflow for Gmail sender extraction",
        "complexity": "low",
        "estimated_duration": sum(s["estimated_duration"] for s in steps),
        "steps": steps,
        "success_criteria": "Final structured list of N senders emitted to UI",
        "error_handling": "Stop on auth errors; otherwise continue with available messages"
    }