import uuid
import time
from contextvars import ContextVar

# stack to support nested spans
_span_stack = ContextVar("span_stack", default=[])


def _now_ms():
    return int(time.time() * 1000)


def start_span(name: str, span_type: str = "INTERNAL"):
    span_id = str(uuid.uuid4())

    stack = list(_span_stack.get())

    parent_id = stack[-1]["span_id"] if stack else None

    span = {
        "span_id": span_id,
        "parent_span_id": parent_id,
        "name": name,
        "type": span_type,
        "start_time": _now_ms()
    }

    stack.append(span)
    _span_stack.set(stack)

    return span


def end_span(extra_data=None):
    stack = list(_span_stack.get())
    if not stack:
        return None

    span = stack.pop()
    _span_stack.set(stack)

    span["end_time"] = _now_ms()
    span["duration_ms"] = span["end_time"] - span["start_time"]

    if extra_data:
        span.update(extra_data)

    return span


def get_current_span():
    stack = _span_stack.get()
    return stack[-1] if stack else None