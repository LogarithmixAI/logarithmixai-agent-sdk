SEVERITY_MAP = {
    "EXCEPTION": "HIGH",
    "HTTP_EXCEPTION": "HIGH",
    "HTTP_CALL": "LOW",
    "INCOMING_REQUEST": "LOW",
    "DB_QUERY": "MEDIUM",
    "LOG": "LOW"
}


def get_severity(event_type):
    return SEVERITY_MAP.get(event_type, "LOW")
