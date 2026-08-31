FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Mainland-China servers can reach the Tsinghua PyPI mirror much faster than
# files.pythonhosted.org. Keep the index configurable and fall back to public
# PyPI so the image remains portable when the mirror is unavailable.
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir \
        --timeout 60 \
        --retries 2 \
        -i "${PIP_INDEX_URL}" \
        -r requirements.txt \
    || pip install --no-cache-dir \
        --timeout 60 \
        --retries 2 \
        -i https://pypi.org/simple \
        -r requirements.txt

# External plugins are loaded by the generic filesystem PluginRuntime.
COPY plugins /opt/tgdrive-plugins
COPY app /app

ENV TGDRIVE_PLUGIN_DIRS=/opt/tgdrive-plugins

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
