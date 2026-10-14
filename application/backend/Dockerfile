FROM python:3.12-slim

WORKDIR /app

# System deps: libpq-dev (psycopg2), libpcap-dev (scapy pcap parsing), curl (compose healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libpcap-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

CMD ["python", "run.py"]
