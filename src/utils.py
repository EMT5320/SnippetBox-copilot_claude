"""Utility functions."""
import hashlib
import json
import uuid
from contextvars import ContextVar
from datetime import datetime

# Context variable for trace_id
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def generate_trace_id() -> str:
    """Generate a unique trace ID."""
    return str(uuid.uuid4())


def get_trace_id() -> str:
    """Get current trace ID from context."""
    return trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    """Set trace ID in context."""
    trace_id_var.set(trace_id)


def compute_content_hash(title: str, content: str) -> str:
    """Compute hash for idempotency check."""
    combined = f"{title.strip()}||{content.strip()}"
    return hashlib.sha256(combined.encode()).hexdigest()


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO 8601 string."""
    if dt is None:
        return None
    return dt.isoformat() + "Z"


def parse_tags(tags_json: str) -> list:
    """Parse tags from JSON string."""
    try:
        return json.loads(tags_json) if tags_json else []
    except:
        return []


def serialize_tags(tags: list) -> str:
    """Serialize tags to JSON string."""
    return json.dumps(tags if tags else [])
