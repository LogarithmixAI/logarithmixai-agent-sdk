from agent_sdk.core.orchestrator import Agent
from agent_sdk.core.pipeline import Pipeline
from agent_sdk.modules.functional.performance import monitor_performance
from functools import wraps


def trace_span(name: str, span_type: str = "custom"):
    pipeline = Pipeline()

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            pipeline.start(name or func.__name__, span_type)
            try:
                return func(*args, **kwargs)
            finally:
                pipeline.end(
                    span_extra_data={
                        "function": f"{func.__module__}.{func.__qualname__}"
                    }
                )

        return wrapper

    return decorator

__all__ = ["Agent", "Pipeline", "monitor_performance", "trace_span"]
