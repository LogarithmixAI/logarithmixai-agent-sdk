import time
import threading

from ..event_builder import build_event
from ..queue import EventQueue
from ..context import generate_trace_id, get_trace_id, clear_trace_id
from ..sanitizer import SanitizerEngine
from ..span_context import start_span, end_span
from ..span_event import build_span_event

# 🔐 sanitizer
sanitizer = SanitizerEngine()


def sanitize_exception(msg: str, limit: int = 200):
    if not msg:
        return ""
    return sanitizer.mask_by_pattern(str(msg))[:limit]


class AgentDjangoMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # 🧵 trace start
        trace_id = generate_trace_id()
        span = start_span("http_request", "HTTP")

        start_time = time.time()

        try:
            response = self.get_response(request)

            duration_ms = int((time.time() - start_time) * 1000)
            status_code = response.status_code

            # 🎯 classification
            if status_code >= 500:
                event_type = "SERVER_ERROR"
                status = "FAILURE"
            elif status_code >= 400:
                event_type = "CLIENT_ERROR"
                status = "FAILURE"
            else:
                event_type = "INCOMING_REQUEST"
                status = "SUCCESS"

            event = build_event(
                event_type=event_type,
                category="APPLICATION",
                status=status,
                metrics={
                    "duration_ms": duration_ms
                },
                data={
                    "path": request.path,
                    "method": request.method,
                    "status_code": status_code,
                    "client_ip": request.META.get("REMOTE_ADDR"),
                    "user_agent": request.META.get("HTTP_USER_AGENT"),
                    "thread": threading.current_thread().name,
                }
            )

            EventQueue.push(event)
            return response

        except Exception as e:

            duration_ms = int((time.time() - start_time) * 1000)

            event = build_event(
                event_type="SERVER_ERROR",
                category="APPLICATION",
                status="FAILURE",
                metrics={
                    "duration_ms": duration_ms
                },
                data={
                    "path": request.path,
                    "method": request.method,
                    "exception_type": type(e).__name__,
                    "message": sanitize_exception(str(e)),
                    "thread": threading.current_thread().name,
                }
            )

            EventQueue.push(event)
            raise

        finally:
            # 🧹 cleanup (VERY IMPORTANT)
            span = end_span({"path": request.url.path})
            EventQueue.push(build_span_event(span))
            clear_trace_id()
