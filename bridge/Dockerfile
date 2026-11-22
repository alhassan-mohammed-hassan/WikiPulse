FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY wikipedia_bridge.py .

CMD ["python", "-u", "wikipedia_bridge.py"]