from agent_sdk.core.event_builder import build_event
import threading

def build_trace_event(trace):

    root = trace["spans"][trace["root_span_id"]]

    return build_event(
        event_type="TRACE_SUMMARY",
        category="SYSTEM",
        status=root["outcome"],
        
        metrics={
            "duration_ms": root.get("duration_ms"),
            "span_count": len(trace["spans"])
        },

        data={
            "trace_id": trace["trace_id"],
            "root_span_id": trace["root_span_id"],

            # 🔥 intelligence
            "outcome": root["outcome"],
            "event_flow": root.get("event_flow", []),

            # 🔥 IMPORTANT ADD
            "event_ids": root.get("event_ids", []),

            # 🔥 span mapping
            "spans": {
                k: {
                    "type": v["type"],
                    "outcome": v.get("outcome"),
                    "parent": v.get("parent_span_id"),
                    'child_span_ids': v.get("child_span_ids", []),
                    "event_ids": v.get("event_ids", []),
                    "event_flow": v.get("event_flow", []),
                    "duration_ms": v.get("duration_ms"),
                    "extra": v.get("extra", {}),

                }
                for k, v in trace["spans"].items()
            }
        }
    )


