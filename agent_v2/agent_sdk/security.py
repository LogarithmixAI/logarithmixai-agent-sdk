import hmac
import hashlib
import json


def generate_signature(secret: str, timestamp: str, payload: dict) -> str:
    message = timestamp + json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature
