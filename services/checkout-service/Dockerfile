FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

COPY app.py .

EXPOSE 8080
ENTRYPOINT ["python3", "-u", "/app/app.py"]
