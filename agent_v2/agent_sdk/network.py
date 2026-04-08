import time
import requests
import traceback
from urllib.parse import urlparse
from .event_builder import build_event
from .queue import EventQueue
from .config import AgentConfig
from .sanitizer import SanitizerEngine
from .context import generate_trace_id, clear_trace_id, get_trace_id
from .span_context import start_span, end_span
from .span_event import build_span_event

sanitizer = SanitizerEngine()

_original_request = None


# ✅ URL sanitizer
def sanitize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        return url


# 📦 Request size calculator
def get_request_size(kwargs):
    try:
        if "data" in kwargs and kwargs["data"]:
            return len(str(kwargs["data"]))
        if "json" in kwargs and kwargs["json"]:
            return len(str(kwargs["json"]))
    except Exception:
        pass
    return 0


# 📦 Safe response preview
def safe_response_preview(response):
    try:
        return response.text[:200]
    except Exception:
        return None


def install_http_patch():

    global _original_request

    if _original_request is not None:
        return

    _original_request = requests.Session.request

    def patched_request(self, method, url, **kwargs):
        # 🔥 Ignore SDK internal endpoint
        if AgentConfig.endpoint:
            try:
                if urlparse(url).netloc == urlparse(AgentConfig.endpoint).netloc:
                    return _original_request(self, method, url, **kwargs)
            except Exception:
                pass

        safe_url = sanitize_url(url)
        parsed = urlparse(url)

        trace_id = get_trace_id()
        created_new_trace = False

         # 🔥 span start
        span = start_span("http_call", "HTTP")

        if not trace_id:
            trace_id = generate_trace_id()
            created_new_trace = True

        # 🔐 sanitize inputs
        headers = sanitizer.sanitize(kwargs.get("headers", {}))
        params = sanitizer.sanitize(kwargs.get("params", {}))

        request_size = get_request_size(kwargs)

        start = time.time()

        try:
            response = _original_request(self, method, url, **kwargs)
            duration_ms = int((time.time() - start) * 1000)

            response_size = len(response.content)

            base_data = {
                "method": method,
                "url": safe_url,
                "host": parsed.netloc,
                "path": parsed.path,
                "status_code": response.status_code,
                "request_size": request_size,
                "response_size": response_size,
                "headers": headers,
                "params": params,
                "timestamp": int(time.time() * 1000)
            }

            # ----------------------------
            # HTTP 4xx / 5xx Handling
            # ----------------------------
            if response.status_code >= 400:

                event = build_event(
                    event_type="HTTP_ERROR",
                    category="NETWORK",
                    status="FAILURE",
                    metrics={
                        "duration_ms": duration_ms
                    },
                    data={
                        **base_data,
                        "error_type": "CLIENT_ERROR" if response.status_code < 500 else "SERVER_ERROR",
                        "response_preview": safe_response_preview(response)
                    }
                )

            else:
                event = build_event(
                    event_type="HTTP_CALL",
                    category="NETWORK",
                    status="SUCCESS",
                    metrics={
                        "duration_ms": duration_ms
                    },
                    data=base_data
                )

            EventQueue.push(event)
            return response

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)

            event = build_event(
                event_type="HTTP_EXCEPTION",
                category="NETWORK",
                status="FAILURE",
                metrics={
                    "duration_ms": duration_ms
                },
                data={
                    "method": method,
                    "url": safe_url,
                    "host": parsed.netloc,
                    "path": parsed.path,
                    "request_size": request_size,
                    "headers": headers,
                    "params": params,
                    "exception_type": type(e).__name__,
                    "message": str(e),
                    "stack_trace": traceback.format_exc(),
                    "timestamp": int(time.time() * 1000)
                }
            )

            EventQueue.push(event)
            raise
            
        finally:
            # 🔥 end span (ALWAYS)
            span = end_span({"url": safe_url})
            EventQueue.push(build_span_event(span))

            # ⚠️ clear only if created here
            if created_new_trace:
                clear_trace_id()

    requests.Session.request = patched_request
