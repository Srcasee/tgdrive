FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

# External plugins are loaded by the generic filesystem PluginRuntime.
COPY plugins /opt/tgdrive-plugins
COPY app /app

ENV TGDRIVE_PLUGIN_DIRS=/opt/tgdrive-plugins

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
