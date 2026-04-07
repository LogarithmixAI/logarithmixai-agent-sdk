from agent_sdk.core.span.span import Span
from agent_sdk.core.severity import SEVERITY_MAP

SEVERITY_ORDER = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4
}

OUTCOME_ORDER = {
    "SUCCESS": 1,
    "DEGRADED": 2,
    "FAILED": 3,
    "CRITICAL": 4
}

class TraceGraph:
    def __init__(self, trace_id):
        self.trace_id = trace_id
        self.root_span_id = None

        # 🔥 fast lookup
        self.spans = {}  # span_id → Span

    def add_span(self, span: Span):
        self.spans[span.span_id] = span

        if span.parent_span_id:
            parent = self.spans.get(span.parent_span_id)
            if parent:
                parent.child_span_ids.append(span.span_id)
        else:
            self.root_span_id = span.span_id

    def get_span(self, span_id):
        return self.spans.get(span_id)

    def add_outcome(self, span:Span):
        outcome = self.derive_span_outcome(span)
        span.outcome = outcome
    
    def build_span_event_flow(self, span:Span):

        flow = list(span.event_flow)  # self events

        for child_id in span.child_span_ids:

            child = self.get_span(child_id)

            if child:
                flow.extend(child.event_flow)

        span.event_flow = self.normalize_flow(flow)

    def normalize_flow(self, flow):

        seen = set()
        ordered = []

        for e in flow:
            if e not in seen:
                seen.add(e)
                ordered.append(e)

        return ordered

    def derive_span_outcome(self, span:Span):

        max_outcome = self.derive_outcome(span.event_flow)

        for child_id in span.child_span_ids:
            child = self.get_span(child_id)

            if not child or not child.outcome:
                continue
            
            child_outcome = child.outcome 

            if OUTCOME_ORDER[child_outcome] > OUTCOME_ORDER[max_outcome]:
                max_outcome = child_outcome

        return max_outcome


    def derive_outcome(self, event_flow):

        max_severity = "LOW"

        for event in event_flow:
            severity = SEVERITY_MAP.get(event, "LOW")

            if SEVERITY_ORDER[severity] > SEVERITY_ORDER[max_severity]:
                max_severity = severity

        if max_severity == "CRITICAL":
            return "CRITICAL"

        if max_severity == "HIGH":
            return "FAILED"

        if max_severity == "MEDIUM":
            return "DEGRADED"

        return "SUCCESS"



    def to_dict(self):
        return {
            "trace_id": self.trace_id,
            "root_span_id": self.root_span_id,
            "spans": {k: v.to_dict() for k, v in self.spans.items()}
        }