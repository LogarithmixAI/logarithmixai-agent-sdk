from functools import wraps
from .span_context import start_span, end_span
from .span_event import build_span_event
from .queue import EventQueue
from .context import get_trace_id


def trace_span(name=None, span_type="FUNCTION"):

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            span = start_span(name or func.__name__, span_type)

            try:
                return func(*args, **kwargs)

            finally:
                span = end_span()
                trace_id = get_trace_id()

                if span:
                    event = build_span_event(span, trace_id)
                    EventQueue.push(event)

        return wrapper

    return decorator