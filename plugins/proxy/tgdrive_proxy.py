import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import socks


class ProxyPlugin:
    """Optional network proxy capability for Telegram clients."""

    name = "proxy"
    version = "0.3.0"
    capabilities = frozenset({"telegram.proxy"})

    def get_proxy(self, account_name=None):
        if os.getenv("TG_PROXY_ENABLED", "false").lower() != "true":
            return None

        proxy_type = os.getenv("TG_PROXY_TYPE", "socks5").lower()
        proxy_types = {
            "socks5": socks.SOCKS5,
            "socks5h": socks.SOCKS5,
            "http": socks.HTTP,
        }
        if proxy_type not in proxy_types:
            raise RuntimeError(f"Unsupported proxy type: {proxy_type}")

        host = os.getenv("TG_PROXY_HOST", "proxy")
        port = int(os.getenv("TG_PROXY_PORT", "1080"))
        username = os.getenv("TG_PROXY_USERNAME") or None
        password = os.getenv("TG_PROXY_PASSWORD") or None
        return (proxy_types[proxy_type], host, port, True, username, password)


def generate_singbox_config(path: str) -> None:
    """Generate the plugin-owned sing-box config from environment variables."""
    required = (
        "TG_PROXY_VLESS_SERVER",
        "TG_PROXY_VLESS_UUID",
        "TG_PROXY_VLESS_SERVER_NAME",
    )
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Missing proxy settings: " + ", ".join(missing))

    import json

    config = {
        "log": {"level": "info"},
        "inbounds": [{
            "type": "socks",
            "tag": "proxy-in",
            "listen": "0.0.0.0",
            "listen_port": int(os.getenv("TG_PROXY_PORT", "1080")),
        }],
        "outbounds": [{
            "type": os.getenv("TG_PROXY_UPSTREAM_TYPE", "vless"),
            "tag": "proxy-out",
            "server": os.environ["TG_PROXY_VLESS_SERVER"],
            "server_port": int(os.getenv("TG_PROXY_VLESS_PORT", "443")),
            "uuid": os.environ["TG_PROXY_VLESS_UUID"],
            "tls": {
                "enabled": True,
                "server_name": os.environ["TG_PROXY_VLESS_SERVER_NAME"],
            },
            "transport": {
                "type": "ws",
                "path": os.getenv("TG_PROXY_VLESS_WS_PATH", "/"),
                "headers": {"Host": os.getenv("TG_PROXY_VLESS_WS_HOST", "")},
            },
        }],
    }
    Path(path).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def run_proxy() -> int:
    """Generate and validate the plugin config, then exec sing-box."""
    config_dir = Path(os.getenv("TG_PROXY_RUNTIME_DIR", "/tmp/tgdrive-proxy"))
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"
    generate_singbox_config(str(config_path))
    result = subprocess.run(["sing-box", "check", "-c", str(config_path)], check=False)
    if result.returncode:
        return result.returncode
    os.execvp("sing-box", ["sing-box", "run", "-c", str(config_path)])
    return 0
