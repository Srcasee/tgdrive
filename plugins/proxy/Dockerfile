FROM ghcr.io/sagernet/sing-box:v1.13.19 AS singbox

FROM python:3.12-slim

COPY --from=singbox /usr/local/bin/sing-box /usr/local/bin/sing-box
COPY tgdrive_proxy.py /opt/tgdrive-proxy/tgdrive_proxy.py

ENV PYTHONPATH=/opt/tgdrive-proxy

# The plugin is loaded directly from the source module. This avoids a
# network-dependent PEP 517 build during the proxy image build.
ENTRYPOINT ["python", "-c", "from tgdrive_proxy import run_proxy; raise SystemExit(run_proxy())"]
