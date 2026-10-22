# Backend Dashboard Layout Interior - Python stdlib + PyMuPDF + SQLite
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8800

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# data (SQLite + gambar denah) disimpan di volume
RUN mkdir -p /app/data/uploads
VOLUME ["/app/data"]

EXPOSE 8800

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8800/api/health', timeout=3).status == 200 else 1)"

CMD ["python", "server.py"]
