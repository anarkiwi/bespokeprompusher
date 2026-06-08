FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    snmp \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt
COPY . .
RUN black --check . && pylint bespokeprompusher tests && pytest --cov=bespokeprompusher --cov-fail-under=85 -v tests/

CMD ["python", "-m", "bespokeprompusher.main"]
