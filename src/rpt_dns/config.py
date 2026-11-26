"""Network-neutral Dynaconf configuration."""

import math
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
                "security_protocol": "",
                "sasl_mechanism": "",
                "sasl_username": "",
                "sasl_password": "",
                "ssl_ca_location": "",
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
    domain = str(settings.DOMAIN).rstrip(".")
    encoded_domain = domain.encode("idna")
    labels = encoded_domain.split(b".")
    if (
        settings.PORT > 65535
        or not domain
        or len(encoded_domain) + 30 > 253
        or any(not label or len(label) > 63 for label in labels)
        or not settings.KAFKA.TOPIC
    ):
        raise ValueError("invalid DNS settings")
    if isinstance(settings.CLOCK_SKEW, bool):
        raise ValueError("clock skew must be a finite non-negative number")
    try:
        settings.CLOCK_SKEW = float(settings.CLOCK_SKEW)
    except (TypeError, ValueError) as error:
        raise ValueError("clock skew must be a finite non-negative number") from error
    if not math.isfinite(settings.CLOCK_SKEW) or settings.CLOCK_SKEW < 0:
        raise ValueError("clock skew must be a finite non-negative number")
    if settings.KAFKA.SECURITY_PROTOCOL:
        if settings.KAFKA.SECURITY_PROTOCOL != "SASL_SSL":
            raise ValueError("Kafka security protocol must be SASL_SSL")
        if not all(
            (
                settings.KAFKA.SASL_MECHANISM == "SCRAM-SHA-512",
                settings.KAFKA.SASL_USERNAME,
                settings.KAFKA.SASL_PASSWORD,
                settings.KAFKA.SSL_CA_LOCATION,
            )
        ):
            raise ValueError("Kafka SASL-SCRAM and TLS credentials are required")
    return settings
