import json
import os
import subprocess
from pathlib import Path


class ProxyPlugin:
    name = "proxy"
    version = "0.5.0"
    capabilities = frozenset({"telegram.proxy"})

    def get_proxy(self, account_name=None):
        if os.getenv("TG_PROXY_ENABLED", "false").lower() != "true":
            return None
        return {
            "type": os.getenv("TG_PROXY_TYPE", "socks5").lower(),
            "host": os.getenv("TG_PROXY_HOST", "proxy"),
            "port": int(os.getenv("TG_PROXY_PORT", "1080")),
            "username": os.getenv("TG_PROXY_USERNAME") or None,
            "password": os.getenv("TG_PROXY_PASSWORD") or None,
        }


def _upstream():
    kind = os.getenv("TG_PROXY_UPSTREAM_TYPE", "vless").lower()
    if kind == "vless":
        required = ["TG_PROXY_VLESS_SERVER", "TG_PROXY_VLESS_UUID", "TG_PROXY_VLESS_SERVER_NAME"]
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise RuntimeError("Missing VLESS settings: " + ", ".join(missing))
        outbound = {
            "type": "vless", "tag": "proxy-out",
            "server": os.environ["TG_PROXY_VLESS_SERVER"],
            "server_port": int(os.getenv("TG_PROXY_VLESS_PORT", "443")),
            "uuid": os.environ["TG_PROXY_VLESS_UUID"],
            "tls": {"enabled": True, "server_name": os.environ["TG_PROXY_VLESS_SERVER_NAME"]},
            "transport": {"type": "ws", "path": os.getenv("TG_PROXY_VLESS_WS_PATH", "/")},
        }
        host = os.getenv("TG_PROXY_VLESS_WS_HOST")
        if host:
            outbound["transport"]["headers"] = {"Host": host}
        return outbound
    if kind in {"socks", "socks5", "http"}:
        host, port = os.getenv("TG_PROXY_UPSTREAM_HOST"), os.getenv("TG_PROXY_UPSTREAM_PORT")
        if not host or not port:
            raise RuntimeError("TG_PROXY_UPSTREAM_HOST and TG_PROXY_UPSTREAM_PORT are required")
        return {"type": "http" if kind == "http" else "socks", "tag": "proxy-out", "server": host, "server_port": int(port)}
    raise RuntimeError(f"Unsupported proxy upstream type: {kind}")


def generate_config(path):
    local_type = os.getenv("TG_PROXY_TYPE", "socks5").lower()
    inbound_type = "http" if local_type == "http" else "socks"
    config = {
        "log": {"level": "info"},
        "inbounds": [{"type": inbound_type, "tag": "proxy-in", "listen": "0.0.0.0", "listen_port": int(os.getenv("TG_PROXY_PORT", "1080"))}],
        "outbounds": [_upstream()],
    }
    Path(path).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def run_proxy():
    runtime = Path(os.getenv("TG_PROXY_RUNTIME_DIR", "/tmp/tgdrive-proxy"))
    runtime.mkdir(parents=True, exist_ok=True)
    config = runtime / "config.json"
    generate_config(config)
    check = subprocess.run(["sing-box", "check", "-c", str(config)], check=False)
    if check.returncode:
        return check.returncode
    os.execvp("sing-box", ["sing-box", "run", "-c", str(config)])


PLUGIN = ProxyPlugin()

if __name__ == "__main__":
    raise SystemExit(run_proxy())
