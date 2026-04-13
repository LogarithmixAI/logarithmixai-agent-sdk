import uuid
from datetime import datetime, timezone
from .config import AgentConfig
from .identity import Identity
from .severity import get_severity
from .context import get_trace_id, generate_trace_id

def current_utc():
    return datetime.now(timezone.utc).isoformat()


def build_event(event_type, category, status, data, metrics=None):
    trace_id = get_trace_id() or generate_trace_id()

    return {
        "meta": {
            "sdk_version": AgentConfig.sdk_version,
            "schema_version": AgentConfig.schema_version,
            "timestamp": current_utc(),
            "trace_id": trace_id,
            "project": AgentConfig.project,
            "environment": AgentConfig.environment
        },

        "identity": Identity.collect(),

        "event": {
            "category": category,
            "type": event_type,
            "severity": get_severity(event_type),
            "status": status,
            "metrics": metrics or {},
            "data": data
        }
    }

