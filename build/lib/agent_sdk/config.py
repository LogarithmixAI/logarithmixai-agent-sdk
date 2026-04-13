class AgentConfig:
    api_key: str = None
    endpoint: str = None
    project: str = None
    environment: str = "production"
    batch_size: int = 20
    flush_interval: int = 5
    enabled: bool = True
