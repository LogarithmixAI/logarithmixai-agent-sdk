import uuid
from contextvars import ContextVar
from agent_sdk.core.span.trace_graph import TraceGraph
from agent_sdk.core.span.span import Span


# 🔥 ContextVars
_trace_id = ContextVar("trace_id", default=None)
_trace_graph = ContextVar("trace_graph", default=None)
_current_span_id = ContextVar("current_span_id", default=None)


# =========================
# 🔹 TRACE
# =========================
class Trace:

    @staticmethod
    def create() -> str:
        trace_id = str(uuid.uuid4())
        _trace_id.set(trace_id)
        return trace_id

    @staticmethod
    def set(trace_id: str):
        _trace_id.set(trace_id)

    @staticmethod
    def get() -> str:
        return _trace_id.get()

    @staticmethod
    def clear():
        _trace_id.set(None)


# =========================
# 🔹 GRAPH
# =========================
class Graph:

    @staticmethod
    def set(graph: TraceGraph):
        _trace_graph.set(graph)

    @staticmethod
    def get() -> TraceGraph:
        return _trace_graph.get()

    @staticmethod
    def clear():
        _trace_graph.set(None)


# =========================
# 🔹 CURRENT SPAN ID
# =========================
class CurrentSpan:

    @staticmethod
    def set(span_id: str):
        _current_span_id.set(span_id)

    @staticmethod
    def set_from_span(span: Span):
        if span:
            _current_span_id.set(span.span_id)

    @staticmethod
    def get() -> str:
        return _current_span_id.get()

    @staticmethod
    def clear():
        _current_span_id.set(None)


### old context trace id
def generate_trace_id():
    trace_id = str(uuid.uuid4())
    _trace_id.set(trace_id)
    return trace_id

def set_trace_id(trace_id: str):
    _trace_id.set(trace_id)

def get_trace_id():
    return _trace_id.get()

def clear_trace_id():
    _trace_id.set(None)