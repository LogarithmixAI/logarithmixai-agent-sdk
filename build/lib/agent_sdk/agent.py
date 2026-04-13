from .config import AgentConfig
from .exceptions import ExceptionTracker
from .sender import Sender
from .network import install_http_patch
from .logging_capture import install_logging


class Agent:
    _initialized = False

    @classmethod
    def init(
        cls,
        *,
        api_key: str,
        endpoint: str,
        project: str,
        environment: str = "production",
        framework: str | None = None,
        app=None,
        db_engine=None,
        auto_exceptions: bool = True,
        auto_http: bool = True,
        auto_logging: bool = True,
    ):
        """
        Initialize Agent SDK with optional framework and DB integration.
        """

        if cls._initialized:
            return

        # ----------------------------
        # Core Configuration
        # ----------------------------
        AgentConfig.api_key = api_key
        AgentConfig.endpoint = endpoint
        AgentConfig.project = project
        AgentConfig.environment = environment

        AgentConfig.auto_exceptions = auto_exceptions
        AgentConfig.auto_http = auto_http
        AgentConfig.auto_logging = auto_logging

        # ----------------------------
        # Install Core Features
        # ----------------------------
        if auto_exceptions:
            ExceptionTracker.install()

        if auto_http:
            install_http_patch()

        if auto_logging:
            install_logging()

        # ----------------------------
        # Framework Integration
        # ----------------------------
        if framework and app:
            framework = framework.lower()

            if framework == "flask":
                from .integrations.flask import init_flask
                init_flask(app)

            elif framework == "fastapi":
                from .integrations.fastapi import init_fastapi
                init_fastapi(app)

            elif framework == "django":
                from .integrations.django import init_django
                init_django()

            else:
                raise ValueError(f"Unsupported framework: {framework}")

        # ----------------------------
        # Database Monitoring
        # ----------------------------
        if db_engine:
            from .database import install_sqlalchemy_monitor
            install_sqlalchemy_monitor(db_engine)

        # ----------------------------
        # Start Background Sender
        # ----------------------------
        Sender.start()

        cls._initialized = True
