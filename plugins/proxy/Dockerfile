FROM python:3.12-slim

ARG SING_BOX_VERSION=1.12.0
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl tar \
    && case "${TARGETARCH}" in \
         amd64) SB_ARCH=amd64 ;; \
         arm64) SB_ARCH=arm64 ;; \
         *) echo "Unsupported architecture: ${TARGETARCH}" && exit 1 ;; \
       esac \
    && curl -fsSL "https://github.com/SagerNet/sing-box/releases/download/v${SING_BOX_VERSION}/sing-box-${SING_BOX_VERSION}-linux-${SB_ARCH}.tar.gz" -o /tmp/sing-box.tgz \
    && tar -xzf /tmp/sing-box.tgz -C /tmp \
    && install -m 0755 "/tmp/sing-box-${SING_BOX_VERSION}-linux-${SB_ARCH}/sing-box" /usr/local/bin/sing-box \
    && rm -rf /tmp/sing-box* \
    && apt-get purge -y curl tar \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /opt/tgdrive-proxy/pyproject.toml
COPY tgdrive_proxy.py /opt/tgdrive-proxy/tgdrive_proxy.py

RUN pip install --no-cache-dir /opt/tgdrive-proxy

ENTRYPOINT ["python", "-c", "from tgdrive_proxy import run_proxy; raise SystemExit(run_proxy())"]
