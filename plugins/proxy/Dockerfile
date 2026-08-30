# Build the Proxy Plugin without depending on GHCR. The upstream sing-box
# release is downloaded as a pinned static musl binary instead.
FROM alpine:3.22 AS singbox

ARG SING_BOX_VERSION=1.13.19
ARG SING_BOX_DOWNLOAD_BASE=https://github.com/SagerNet/sing-box/releases/download
ARG TARGETARCH

RUN apk add --no-cache ca-certificates curl tar \
    && case "${TARGETARCH}" in \
         amd64) \
           ASSET="sing-box-${SING_BOX_VERSION}-linux-amd64-musl.tar.gz" \
           EXTRACTED_DIR="sing-box-${SING_BOX_VERSION}-linux-amd64-musl" \
           SHA256="150456f94fcf936fc2519de28d856422fb671a1ff181cd909b78f20e208fdcb8" \
           ;; \
         arm64) \
           ASSET="sing-box-${SING_BOX_VERSION}-linux-arm64-musl.tar.gz" \
           EXTRACTED_DIR="sing-box-${SING_BOX_VERSION}-linux-arm64-musl" \
           SHA256="5146181884310ea2381e085ef504005c81bd09f80721542127efb0a73f12cd2f" \
           ;; \
         *) echo "Unsupported TARGETARCH=${TARGETARCH}; supported: amd64, arm64" >&2; exit 1 ;; \
       esac \
    && URL="${SING_BOX_DOWNLOAD_BASE}/v${SING_BOX_VERSION}/${ASSET}" \
    && curl -fsSL --retry 5 --retry-delay 2 "${URL}" -o /tmp/sing-box.tar.gz \
    && echo "${SHA256}  /tmp/sing-box.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/sing-box.tar.gz -C /tmp \
    && install -m 0755 "/tmp/${EXTRACTED_DIR}/sing-box" /usr/local/bin/sing-box \
    && sing-box version

FROM python:3.12-slim

COPY --from=singbox /usr/local/bin/sing-box /usr/local/bin/sing-box
COPY plugin.py /opt/tgdrive-proxy/plugin.py

ENTRYPOINT ["python", "/opt/tgdrive-proxy/plugin.py"]
