# sing-box is vendored in the repository at a pinned version.
# Docker builds never download sing-box from GitHub or Alpine repositories.
FROM python:3.12-slim

ARG TARGETARCH=amd64

COPY bin/sing-box-linux-${TARGETARCH} /usr/local/bin/sing-box
COPY server.py /opt/tgdrive-proxy/server.py

RUN chmod 0755 /usr/local/bin/sing-box

ENTRYPOINT ["python", "/opt/tgdrive-proxy/server.py"]
