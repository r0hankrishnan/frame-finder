FROM python:3.13-slim

WORKDIR /app

COPY . .

# CPU-only torch — omits ~1.5GB of CUDA libraries you don't use (no GPU on Railway)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir .

CMD python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT