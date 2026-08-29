FROM ghcr.io/sagernet/sing-box:v1.13.19 AS singbox

FROM python:3.12-slim

COPY --from=singbox /usr/local/bin/sing-box /usr/local/bin/sing-box
COPY plugin.py /opt/tgdrive-proxy/plugin.py

ENTRYPOINT ["python", "/opt/tgdrive-proxy/plugin.py"]
