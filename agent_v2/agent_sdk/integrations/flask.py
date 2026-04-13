import time
import threading

from flask import request, g
from ..event_builder import build_event
from ..queue import EventQueue
from ..context import generate_trace_id, get_trace_id, clear_trace_id
from ..span_context import start_span, end_span
from ..span_event import build_span_event


def init_flask(app):

    @app.before_request
    def _start_timer():
        g._agent_start_time = time.time()
        g._span = start_span("http_request", "HTTP")

    @app.after_request
    def _log_request(response):

        try:
            start_time = getattr(g, "_agent_start_time", time.time())

            duration_ms = int(
                (time.time() - start_time) * 1000
            )

            status_code = response.status_code

            # 🎯 classification
            if status_code >= 500:
                g._error_logged = True
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
                    "client_ip": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent"),
                    "thread": threading.current_thread().name,
                }
            )


            EventQueue.push(event)

        except Exception:
            pass  # never break app

        return response

    @app.teardown_request
    def _teardown(exc):

        try:
            # ⏱ duration
            start_time = getattr(g, "_agent_start_time", time.time())
            duration_ms = int((time.time() - start_time) * 1000)

            # ❗ if exception → log it
            if exc is not None  and not getattr(g, "_error_logged", False):
                event = build_event(
                    event_type="SERVER_ERROR",
                    category="APPLICATION",
                    status="FAILURE",
                    metrics={"duration_ms": duration_ms},
                    data={
                        "path": request.path,
                        "method": request.method,
                        "exception_type": type(exc).__name__,
                        "thread": threading.current_thread().name,
                    }
                )
                EventQueue.push(event)

            # ✅ ALWAYS end span
            span = end_span({"path": request.path})
            EventQueue.push(build_span_event(span))

        except Exception as e:
           pass

        finally:
            # ✅ ALWAYS clear trace
            clear_trace_id()