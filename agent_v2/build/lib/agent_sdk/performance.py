import time
import uuid
import random
from functools import wraps
from .event_builder import build_event
from .queue import EventQueue


DEFAULT_SLOW_THRESHOLD_MS = 500


def monitor_performance(threshold_ms=DEFAULT_SLOW_THRESHOLD_MS, sample_rate=1.0):

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            # 🔥 Sampling (performance safe)
            if random.random() > sample_rate:
                return func(*args, **kwargs)
            start = time.time()
            exception = None

            try:
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                exception = e
                raise

            finally:
                duration_ms = int((time.time() - start) * 1000)

                if exception:
                    event_type = "FUNCTION_EXCEPTION"
                    status = "FAILURE"

                elif duration_ms >= threshold_ms:
                    event_type = "SLOW_FUNCTION"
                    status = "WARNING"

                else:
                    event_type = "FUNCTION_CALL"
                    status = "SUCCESS"

                event = build_event(
                    event_type=event_type,
                    category="APPLICATION",
                    status=status,
                    metrics={
                        "duration_ms": duration_ms
                    },
                    data={
                        "function": f"{func.__module__}.{func.__qualname__}",
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                    }
                )

                EventQueue.push(event)

        return wrapper

    return decorator