FROM ghcr.io/sagernet/sing-box:v1.13.19 AS singbox

FROM python:3.12-slim

COPY --from=singbox /usr/local/bin/sing-box /usr/local/bin/sing-box

COPY pyproject.toml /opt/tgdrive-proxy/pyproject.toml
COPY tgdrive_proxy.py /opt/tgdrive-proxy/tgdrive_proxy.py

RUN pip install --no-cache-dir --no-build-isolation /opt/tgdrive-proxy

ENTRYPOINT ["python", "-c", "from tgdrive_proxy import run_proxy; raise SystemExit(run_proxy())"]
