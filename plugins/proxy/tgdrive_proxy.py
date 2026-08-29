import json
import os
import subprocess
from pathlib import Path


class ProxyPlugin:
    """Optional network proxy capability for Telegram clients."""

    name = "proxy"
    version = "0.4.0"
    capabilities = frozenset({"telegram.proxy"})

    def get_proxy(self, account_name=None):
        if os.getenv("TG_PROXY_ENABLED", "false").lower() != "true":
            return None
        proxy_type = os.getenv("TG_PROXY_TYPE", "socks5").lower()
        if proxy_type not in {"socks5", "socks5h", "http"}:
            raise RuntimeError(f"Unsupported local proxy type: {proxy_type}")
        host = os.getenv("TG_PROXY_HOST", "proxy")
        port = int(os.getenv("TG_PROXY_PORT", "1080"))
        username = os.getenv("TG_PROXY_USERNAME") or None
        password = os.getenv("TG_PROXY_PASSWORD") or None
        # Pyrogram accepts a PySocks-compatible tuple, but the proxy plugin
        # must not make the Core image install a proxy-specific dependency.
        # Return a standard descriptor; the Telegram adapter owns translation.
        return {
            "type": proxy_type,
            "host": host,
            "port": port,
            "username": username,
            "password": password,
        }


def _local_inbound():
    proxy_type = os.getenv("TG_PROXY_TYPE", "socks5").lower()
    if proxy_type in {"socks5", "socks5h"}:
        return {"type": "socks", "tag": "proxy-in", "listen": "0.0.0.0", "listen_port": int(os.getenv("TG_PROXY_PORT", "1080"))}
    if proxy_type == "http":
        return {"type": "http", "tag": "proxy-in", "listen": "0.0.0.0", "listen_port": int(os.getenv("TG_PROXY_PORT", "1080"))}
    raise RuntimeError(f"Unsupported local proxy type: {proxy_type}")


def _upstream_outbound():
    upstream_type = os.getenv("TG_PROXY_UPSTREAM_TYPE", "vless").lower()

    if upstream_type == "vless":
        required = ("TG_PROXY_VLESS_SERVER", "TG_PROXY_VLESS_UUID", "TG_PROXY_VLESS_SERVER_NAME")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise RuntimeError("Missing VLESS settings: " + ", ".join(missing))
        outbound = {
            "type": "vless",
            "tag": "proxy-out",
            "server": os.environ["TG_PROXY_VLESS_SERVER"],
            "server_port": int(os.getenv("TG_PROXY_VLESS_PORT", "443")),
            "uuid": os.environ["TG_PROXY_VLESS_UUID"],
            "tls": {"enabled": True, "server_name": os.environ["TG_PROXY_VLESS_SERVER_NAME"]},
            "transport": {
                "type": "ws",
                "path": os.getenv("TG_PROXY_VLESS_WS_PATH", "/"),
            },
        }
        ws_host = os.getenv("TG_PROXY_VLESS_WS_HOST")
        if ws_host:
            outbound["transport"]["headers"] = {"Host": ws_host}
        return outbound

    if upstream_type in {"socks", "socks5"}:
        host = os.getenv("TG_PROXY_UPSTREAM_HOST")
        port = os.getenv("TG_PROXY_UPSTREAM_PORT")
        if not host or not port:
            raise RuntimeError("TG_PROXY_UPSTREAM_HOST and TG_PROXY_UPSTREAM_PORT are required")
        return {"type": "socks", "tag": "proxy-out", "server": host, "server_port": int(port)}

    if upstream_type == "http":
        host = os.getenv("TG_PROXY_UPSTREAM_HOST")
        port = os.getenv("TG_PROXY_UPSTREAM_PORT")
        if not host or not port:
            raise RuntimeError("TG_PROXY_UPSTREAM_HOST and TG_PROXY_UPSTREAM_PORT are required")
        return {"type": "http", "tag": "proxy-out", "server": host, "server_port": int(port)}

    raise RuntimeError(f"Unsupported proxy upstream type: {upstream_type}")


def generate_singbox_config(path: str) -> None:
    config = {
        "log": {"level": "info"},
        "inbounds": [_local_inbound()],
        "outbounds": [_upstream_outbound()],
    }
    Path(path).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def run_proxy() -> int:
    config_dir = Path(os.getenv("TG_PROXY_RUNTIME_DIR", "/tmp/tgdrive-proxy"))
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"
    generate_singbox_config(str(config_path))
    result = subprocess.run(["sing-box", "check", "-c", str(config_path)], check=False)
    if result.returncode:
        return result.returncode
    os.execvp("sing-box", ["sing-box", "run", "-c", str(config_path)])
    return 0


def main():
    return run_proxy()
