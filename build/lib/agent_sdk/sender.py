import threading
import time
import requests
from .queue import EventQueue
from .config import AgentConfig
from .metrics import EndpointMetrics

class Sender:
    @staticmethod
    def start():
        thread = threading.Thread(target=Sender._run, daemon=True)
        thread.start()

    @staticmethod
    def _run():
        while True:
            time.sleep(AgentConfig.flush_interval)
            batch = EventQueue.flush()
            if not batch:
                continue

            metrics_snapshot = EndpointMetrics.snapshot()

            if metrics_snapshot:
                requests.post(
                    AgentConfig.endpoint,
                    json={
                        "type": "METRICS",
                        "project": AgentConfig.project,
                        "metrics": metrics_snapshot
                    }
                )

            try:
                requests.post(
                    AgentConfig.endpoint,
                    json={
                        "api_key": AgentConfig.api_key,
                        "project": AgentConfig.project,
                        "events": batch
                    },
                    timeout=2
                )
            except Exception:
                pass  # NEVER crash client

