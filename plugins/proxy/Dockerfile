# Build the Proxy Plugin without depending on Alpine package indexes.
# The upstream sing-box release is downloaded as a pinned static musl binary.
FROM python:3.12-slim AS singbox

ARG SING_BOX_VERSION=1.13.19
ARG SING_BOX_DOWNLOAD_BASE=https://github.com/SagerNet/sing-box/releases/download
ARG TARGETARCH

RUN python - <<'PY'
import hashlib
import os
import pathlib
import tarfile
import urllib.request

version = os.environ.get("SING_BOX_VERSION", "1.13.19")
base = os.environ.get(
    "SING_BOX_DOWNLOAD_BASE",
    "https://github.com/SagerNet/sing-box/releases/download",
)
arch = os.environ.get("TARGETARCH", "amd64")
assets = {
    "amd64": (
        f"sing-box-{version}-linux-amd64-musl.tar.gz",
        f"sing-box-{version}-linux-amd64-musl",
        "150456f94fcf936fc2519de28d856422fb671a1ff181cd909b78f20e208fdcb8",
    ),
    "arm64": (
        f"sing-box-{version}-linux-arm64-musl.tar.gz",
        f"sing-box-{version}-linux-arm64-musl",
        "5146181884310ea2381e085ef504005c81bd09f80721542127efb0a73f12cd2f",
    ),
}
if arch not in assets:
    raise SystemExit(f"Unsupported TARGETARCH={arch}; supported: amd64, arm64")

asset, extracted_dir, expected_sha256 = assets[arch]
url = f"{base}/v{version}/{asset}"
out = pathlib.Path("/tmp/sing-box.tar.gz")
print(f"Downloading sing-box {version} from {url}", flush=True)
urllib.request.urlretrieve(url, out)
actual_sha256 = hashlib.sha256(out.read_bytes()).hexdigest()
if actual_sha256 != expected_sha256:
    raise SystemExit(
        f"sing-box SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}"
    )

with tarfile.open(out, "r:gz") as archive:
    member = archive.getmember(f"{extracted_dir}/sing-box")
    member.name = "sing-box"
    archive.extract(member, "/tmp")

binary = pathlib.Path("/tmp/sing-box")
binary.chmod(0o755)
print(f"sing-box {version} SHA256 verified", flush=True)
PY

FROM python:3.12-slim

COPY --from=singbox /tmp/sing-box /usr/local/bin/sing-box
COPY plugin.py /opt/tgdrive-proxy/plugin.py

ENTRYPOINT ["python", "/opt/tgdrive-proxy/plugin.py"]
