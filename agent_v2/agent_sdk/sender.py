import threading
import time
import requests
from datetime import datetime, timezone
from .queue import EventQueue
from .config import AgentConfig
from .security import generate_signature
import json


def current_utc():
    return datetime.now(timezone.utc).isoformat()


class Sender:

    RETRY_LIMIT = 5
    BASE_BACKOFF = 1  # seconds

    @staticmethod
    def start():
        thread = threading.Thread(target=Sender._run, daemon=True)
        thread.start()

    @staticmethod
    def _run():
        while True:
            time.sleep(5)

            batch = EventQueue.flush()
            if not batch:
                continue

            Sender._send_with_retry(batch)

    @staticmethod
    def _send_with_retry(batch):

        if not AgentConfig.api_secret:
            return

        payload = {
            "batch_meta": {
                "sdk_version": AgentConfig.sdk_version,
                "schema_version": AgentConfig.schema_version,
                "sent_at": current_utc(),
                "event_count": len(batch),
                "project": AgentConfig.project,
                "environment": AgentConfig.environment
            },
            "events": batch
        }

        # Stable JSON body
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)

        attempt = 0

        while attempt < Sender.RETRY_LIMIT:
            try:
                timestamp = current_utc()

                signature = generate_signature(
                    AgentConfig.api_secret,
                    timestamp,
                    body
                )

                headers = {
                    "X-API-KEY": AgentConfig.api_key,
                    "X-TIMESTAMP": timestamp,
                    "X-SIGNATURE": signature,
                    "Content-Type": "application/json"
                }

                response = requests.post(
                    AgentConfig.endpoint,
                    data=body,
                    headers=headers,
                    timeout=3
                )

                if response.status_code < 500:
                    return

            except Exception:
                pass

            backoff_time = Sender.BASE_BACKOFF * (2 ** attempt)
            time.sleep(backoff_time)
            attempt += 1
