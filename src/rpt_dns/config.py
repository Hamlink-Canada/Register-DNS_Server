"""Network-neutral Dynaconf configuration."""

import os
from pathlib import Path

from dynaconf import Dynaconf
from dynaconf.loaders import env_loader


def load_settings(**overrides):
    settings = Dynaconf(
        envvar_prefix="RPT",
        environments=False,
        merge_enabled=True,
        settings_files=[],
        load_dotenv=False,
    )
    settings.update(
        {
            "host": "0.0.0.0",
            "port": 5054,
            "domain": "nodes.example.org",
            "cache_size": 10000,
            "max_lifetime": 86400,
            "clock_skew": 30,
            "workers": 32,
            "kafka": {
                "bootstrap": "localhost:9092",
                "topic": "rpt.registrations",
                "group": "rpt-dns",
            },
        }
    )
    directory = Path(os.environ.get("RPT_CONFIG_DIR", ".")).resolve()
    for name in ("settings.toml", ".secrets.toml"):
        if (directory / name).exists():
            settings.load_file(path=str(directory / name))
    env_loader.load(settings, env="RPT")
    settings.update(overrides, merge=True)
    if not all(
        type(v) is int and v > 0
        for v in [settings.PORT, settings.CACHE_SIZE, settings.MAX_LIFETIME, settings.WORKERS]
    ):
        raise ValueError("invalid numeric DNS setting")
    if settings.PORT > 65535 or not settings.DOMAIN or not settings.KAFKA.TOPIC:
        raise ValueError("invalid DNS settings")
    return settings
