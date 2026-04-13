import re
from agent_sdk.config.setting import AgentConfig


DEFAULT_SENSITIVE_KEYS = {
    # Auth
    "authorization", "proxy-authorization", "token", "access_token",
    "refresh_token", "id_token", "jwt", "session", "sessionid",
    "session_id", "cookie", "set-cookie", "x-api-key", "api_key",
    "apikey", "secret", "client_secret",

    # Passwords
    "password", "passwd", "pwd", "passcode", "pin", "otp",

    # PII
    "email", "phone", "mobile", "aadhaar", "pan", "ssn",
    "dob", "date_of_birth",

    # Payment
    "card_number", "credit_card", "cvv", "expiry",
    "upi_id", "bank_account", "ifsc",

    # Headers
    "x-forwarded-for", "x-real-ip"
}


class SanitizerEngine:

    def __init__(self):
        self.sensitive_keys = self._load_keys()
        self.patterns = self._load_patterns()

    def _load_keys(self):
        keys = set(DEFAULT_SENSITIVE_KEYS)

        if AgentConfig.sensitive_keys:
            keys.update([k.lower() for k in AgentConfig.sensitive_keys])

        return keys

    def _load_patterns(self):
        return [re.compile(p) for p in AgentConfig.sensitive_patterns]

    # 🔍 key detection
    def is_sensitive_key(self, key: str):
        key = key.lower()
        return any(s in key for s in self.sensitive_keys)

    # 🔐 mask value
    def mask_value(self, value):
        if not value:
            return value

        value = str(value)

        if len(value) <= 8:
            return "****"

        return value[:4] + "****" + value[-4:]

    # 🔍 regex detection
    def mask_by_pattern(self, value: str):
        value = str(value)

        for pattern in self.patterns:
            if pattern.search(value):
                return self.mask_value(value)

        return value

    # 🔁 recursive sanitize
    def sanitize(self, data):
        if isinstance(data, dict):
            return {
                k: self._sanitize_value(k, v)
                for k, v in data.items()
            }

        elif isinstance(data, list):
            return [self.sanitize(v) for v in data]

        return self.mask_by_pattern(data)

    def _sanitize_value(self, key, value):

        # 🔐 key आधारित masking
        if self.is_sensitive_key(key):
            return self.mask_value(value)

        # 🔁 recursive
        if isinstance(value, dict) or isinstance(value, list):
            return self.sanitize(value)

        # 🔍 pattern based
        return self.mask_by_pattern(value)