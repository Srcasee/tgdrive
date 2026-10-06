# Frontend build stage
FROM node:20-bookworm-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Core runtime
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir --prefer-binary --timeout 60 --retries 2 -i "${PIP_INDEX_URL}" -r requirements.txt || pip install --no-cache-dir --prefer-binary --timeout 60 --retries 2 -i https://pypi.org/simple -r requirements.txt
COPY plugins /opt/tgdrive-plugins
COPY app /app
COPY --from=frontend-build /frontend/dist /app/frontend/dist
ENV TGDRIVE_PLUGIN_DIRS=/opt/tgdrive-plugins
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
