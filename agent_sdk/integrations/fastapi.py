import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from ..metrics import EndpointMetrics
from ..queue import EventQueue


class AgentFastAPIMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            EventQueue.push({
                "type": "INCOMING_REQUEST",
                "framework": "fastapi",
                "path": request.url.path,
                "method": request.method,
                "status": response.status_code,
                "duration": duration
            })

            EndpointMetrics.record(
                path=request.path,
                status=response.status_code,
                duration=duration
            )

            return response

        except Exception as e:
            duration = time.time() - start_time

            EventQueue.push({
                "type": "FASTAPI_ERROR",
                "path": request.url.path,
                "method": request.method,
                "message": str(e),
                "duration": duration
            })

            raise e


def init_fastapi(app):
    app.add_middleware(AgentFastAPIMiddleware)
