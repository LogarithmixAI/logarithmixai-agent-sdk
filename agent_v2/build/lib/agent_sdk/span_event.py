from .event_builder import build_event

def build_span_event(span):

    return build_event(
        event_type="SPAN",
        category="PERFORMANCE",
        status="SUCCESS",
        metrics={
            "duration_ms": span["duration_ms"]
        },
        data={
            "span_id": span["span_id"],
            "parent_span_id": span["parent_span_id"],
            "name": span["name"],
            "type": span["type"],
        }
    )