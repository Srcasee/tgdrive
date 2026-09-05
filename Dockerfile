FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Prefer prebuilt wheels so first-time deployment does not compile native
# extensions on the host. Keep the mirror configurable and fall back to PyPI.
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir \
        --prefer-binary \
        --timeout 60 \
        --retries 2 \
        -i "${PIP_INDEX_URL}" \
        -r requirements.txt \
    || pip install --no-cache-dir \
        --prefer-binary \
        --timeout 60 \
        --retries 2 \
        -i https://pypi.org/simple \
        -r requirements.txt

# External plugins are loaded by the generic filesystem PluginRuntime.
COPY plugins /opt/tgdrive-plugins
COPY app /app

ENV TGDRIVE_PLUGIN_DIRS=/opt/tgdrive-plugins

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
