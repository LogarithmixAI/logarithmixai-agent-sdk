import socket
import platform
import os
import uuid
from pathlib import Path


class Identity:

    _cached_identity = None
    INSTANCE_FILE = Path.home() / ".agent_instance_id"

    @classmethod
    def _get_or_create_instance_id(cls):
        try:
            if cls.INSTANCE_FILE.exists():
                return cls.INSTANCE_FILE.read_text().strip()

            instance_id = str(uuid.uuid4())
            cls.INSTANCE_FILE.write_text(instance_id)
            return instance_id

        except Exception:
            # fallback if filesystem restricted (containers, serverless)
            return str(uuid.uuid4())

    @classmethod
    def collect(cls, app_version="1.0.0", region="unknown", include_pid=True):

        if cls._cached_identity:
            return cls._cached_identity

        hostname = socket.gethostname()

        identity = {
            "hostname": hostname,
            "region": region,
            "os": platform.system(),
            "os_version": platform.release(),
            "python_version": platform.python_version(),
            "app_version": app_version,
            "instance_id": cls._get_or_create_instance_id()
        }

        # process_id optional (useful in VM, less useful in containers)
        if include_pid:
            identity["process_id"] = os.getpid()

        cls._cached_identity = identity
        return identity