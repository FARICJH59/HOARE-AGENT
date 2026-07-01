FROM python:3.11-slim

WORKDIR /app

# Install system deps (needed for z3-solver native build)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ make libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV HOARE_HTTP_PORT=8080
ENV HOARE_GRPC_PORT=50051
ENV HOARE_USE_MOCK_LLM=0

EXPOSE 8080 50051

CMD ["python", "main.py"]
