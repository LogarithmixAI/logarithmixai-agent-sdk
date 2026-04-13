import time
import threading

from agent_sdk.core.sanitizer import SanitizerEngine
from agent_sdk.core.pipeline import Pipeline

# 🔐 sanitizer
sanitizer = SanitizerEngine()
pipeline = Pipeline()


def sanitize_exception(msg: str, limit: int = 200):
    if not msg:
        return ""
    return sanitizer.mask_by_pattern(str(msg))[:limit]


# 🔥 CLASSIFIER (same across all frameworks)
def classify_event(status_code, duration, exc, timeout_threshold=4000, slow_threshold=1000):

    is_slow = duration and duration > slow_threshold
    is_timeout = duration and duration > timeout_threshold

    if is_timeout:
        return "REQUEST_TIMEOUT"

    if exc:
        if is_slow:
            return "REQUEST_SLOW_FAILURE"
        return "REQUEST_FAILED_APPLICATION"

    if status_code == 404:
        return "REQUEST_FAILED_ROUTING"

    if status_code and status_code >= 500:
        if is_slow:
            return "REQUEST_SLOW_FAILURE"
        return "REQUEST_FAILED_SERVER"

    if status_code and status_code >= 400:
        return "REQUEST_FAILED_CLIENT"

    if is_slow:
        return "REQUEST_SUCCESS_SLOW"

    return "REQUEST_SUCCESS_FAST"


class AgentDjangoMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        pipeline.create_trace(reset=True)
        pipeline.start("request", "http_request")  # main request span

        start_time = time.time()

        # 🔹 INCOMING REQUEST
        pipeline.process(
            event_type="INCOMING_REQUEST",
            category="APPLICATION",
            status="STARTED",
            metrics={},
            data={
                "path": request.path,
                "method": request.method,
                "client_ip": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT"),
                "thread": threading.current_thread().name,
            },
            span_extra_data={"path": request.path}
        )

        exc = None
        status_code = None

        try:
            response = self.get_response(request)
            status_code = response.status_code

            # 🔹 RESPONSE EVENT
            pipeline.process(
                event_type="RESPONSE",
                category="APPLICATION",
                status="SUCCESS" if status_code < 400 else "FAILURE",
                metrics={},
                data={
                    "path": request.path,
                    "method": request.method,
                    "status_code": status_code,
                    "client_ip": request.META.get("REMOTE_ADDR"),
                    "user_agent": request.META.get("HTTP_USER_AGENT"),
                    "thread": threading.current_thread().name,
                },
                span_extra_data={"path": request.path}
            )

            return response

        except Exception as e:
            exc = e
            status_code = 500
            pipeline.start("request_processing", "application_logic")
            pipeline.process(
                event_type="REQUEST_EXCEPTION",
                category="APPLICATION",
                status="FAILURE",
                metrics={},
                data={
                    "path": request.path,
                    "method": request.method,
                    "exception_type": type(e).__name__,
                    "message": sanitize_exception(str(e)),
                    "thread": threading.current_thread().name,
                    "status_code": status_code
                },
                span_extra_data={"path": request.path}
            )

            pipeline.end(
                span_extra_data={
                    "stage": "processing",
                    "path": request.path,
                    "method": request.method,
                    "exception_type": type(e).__name__,
                    "status_code": status_code
                }
            )
            raise

        finally:
            if not pipeline.has_active_trace():
                return

            # 🔥 FINAL CLASSIFICATION (TEARDOWN EQUIVALENT)

            duration = int((time.time() - start_time) * 1000)

            event_type = classify_event(
                status_code=status_code,
                duration=duration,
                exc=exc
            )

            pipeline.process(
                event_type="REQUEST_VERDICT",
                category="FINAL",
                status="FAILURE" if exc or (status_code and status_code >= 400) else "SUCCESS",
                metrics={
                    "status_code": status_code
                },
                data={
                    "classification": event_type,
                    "path": request.path,
                    "method": request.method,
                    "exception_type": type(exc).__name__ if exc else None,
                    "is_timeout": duration > 4000,
                    "is_slow": duration > 1000,
                    "thread": threading.current_thread().name,
                },
                span_extra_data={"path": request.path}
            )
            
            pipeline.end(
                span_extra_data={
                    "classification": event_type,
                    "path": request.path,
                    "method": request.method,
                    "status_code": status_code,
                    "duration_ms": duration,
                    "exception_type": type(exc).__name__ if exc else None,
                }
            )   # end main request span

            pipeline.clear_trace(force_clear=True)  # ensure trace is cleared
