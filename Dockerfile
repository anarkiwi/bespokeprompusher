FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    snmp \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

FROM base AS test
RUN pip install --no-cache-dir -r requirements-dev.txt
CMD ["pytest", "-v", "tests/"]

FROM base AS production
CMD ["python", "-m", "bespokeprompusher.main"]
