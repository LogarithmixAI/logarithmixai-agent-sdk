import hmac
import hashlib
import json


def _normalize_payload(payload) -> str:
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def generate_signature(secret: str, timestamp: str, payload) -> str:
    message = timestamp + _normalize_payload(payload)
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature
