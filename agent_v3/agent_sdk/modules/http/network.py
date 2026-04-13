import time
import requests
import traceback
import threading
from urllib.parse import urlparse
from agent_sdk.config.setting import AgentConfig
from agent_sdk.core.sanitizer import SanitizerEngine
from agent_sdk.core.pipeline import Pipeline

sanitizer = SanitizerEngine()
pipeline = Pipeline()
_original_request = None

endpoint_netloc = urlparse(AgentConfig.endpoint).netloc if AgentConfig.endpoint else None

def classify_http(status_code, duration, exc, slow_threshold=1000, timeout_threshold=4000):

    is_slow = duration and duration >= slow_threshold
    is_timeout = duration and duration >= timeout_threshold

    # 🔴 1. Timeout (highest priority)
    if is_timeout:
        return "HTTP_TIMEOUT"

    # 🔴 2. Exception
    if exc:
        if is_slow:
            return "HTTP_SLOW_FAILURE"
        return "HTTP_EXCEPTION"

    # 🔴 3. Specific 4xx cases
    if status_code == 401:
        return "HTTP_UNAUTHORIZED"

    if status_code == 403:
        return "HTTP_FORBIDDEN"

    if status_code == 404:
        return "HTTP_NOT_FOUND"

    if status_code == 429:
        return "HTTP_RATE_LIMITED"

    # 🔴 4. Specific 5xx cases (infra insight)
    if status_code == 502:
        return "HTTP_BAD_GATEWAY"

    if status_code == 503:
        return "HTTP_SERVICE_UNAVAILABLE"

    if status_code == 504:
        return "HTTP_GATEWAY_TIMEOUT"

    # 🔴 5. Generic server error
    if status_code and status_code >= 500:
        if is_slow:
            return "HTTP_SLOW_FAILURE"
        return "HTTP_FAILED_SERVER"

    # 🔴 6. Generic client error
    if status_code and status_code >= 400:
        return "HTTP_FAILED_CLIENT"

    # 🟢 7. Success cases
    if is_slow:
        return "HTTP_SLOW"

    return "HTTP_SUCCESS"

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

        is_internal_call = False
        
        # 🔥 Ignore SDK internal endpoint
        if AgentConfig.endpoint:
            try:
                if urlparse(url).netloc == urlparse(AgentConfig.endpoint).netloc:
                    is_internal_call = True
                    return _original_request(self, method, url, **kwargs)
            except Exception as e:
                print(f"exception in networ.py 'AgentConfig.endpoint': {e}")

        safe_url = sanitize_url(url)
        parsed = urlparse(url)

    
        pipeline.create_trace()
        pipeline.start("External_HTTP_Call", "http_call") # start main request span
        start_time = time.time()

        # 🔐 sanitize inputs
        headers = sanitizer.sanitize(kwargs.get("headers", {}))
        params = sanitizer.sanitize(kwargs.get("params", {}))
        request_size = get_request_size(kwargs)

        exc = None
        status_code = None

        try:
            response = _original_request(self, method, url, **kwargs)
            status_code = response.status_code
            response_size = len(response.content)

            return response

        except Exception as e:
            exc = e
            print(e)
            raise
            
        finally:

            if is_internal_call:
                return
            try:
                duration_ms = int((time.time() - start_time) * 1000)
                event_type = classify_http(status_code, duration_ms, exc)

                pipeline.process(
                    event_type=event_type,
                    category="NETWORK",
                    status="FAILURE" if exc or (status_code and status_code >= 400) else "SUCCESS",
                    metrics={
                        "duration_ms": duration_ms,
                        "status_code": status_code
                    },
                    data={
                        "method": method,
                        "url": safe_url,
                        "host": parsed.netloc,
                        "path": parsed.path,
                        "request_size": request_size,
                        "response_size": len(response.content) if status_code else None,
                        "response_preview": safe_response_preview(response) if status_code else None,
                        "headers": headers,
                        "params": params,
                        "exception_type": type(exc).__name__ if exc else None,
                        "stack_trace": traceback.format_exc() if exc else None,
                        "message": str(exc) if exc else None,
                        "is_slow": duration_ms >= 1000,
                        "is_timeout": duration_ms >= 4000,
                        "thread": threading.current_thread().name
                    },
                )
            except Exception as e:
                # never break app due to our instrumentation
                print(f"Error in HTTP instrumentation: {e}")
                traceback.print_exc()

            pipeline.end(
                span_extra_data={
                    "url": safe_url,
                    "method": method,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "host": parsed.netloc,
                    "path": parsed.path,
                    "error": True if exc else False,
                    "exception_type": type(exc).__name__ if exc else None,
                    "is_slow": duration_ms >= 1000
                }
            ) # end http_call span
            pipeline.clear_trace()

    requests.Session.request = patched_request
