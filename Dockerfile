FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
COPY plugins/tgdrive-proxy-socks5 /opt/tgdrive-proxy-socks5

RUN pip install \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt \
    /opt/tgdrive-proxy-socks5

COPY app /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
