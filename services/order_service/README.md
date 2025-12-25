# Order Service

Internal service that owns the trading order domain.

## Endpoints

- `GET /health` - Health check
- `GET /internal/hello` - Hello endpoint

## Run Instructions

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the service

```bash
uvicorn main:app --reload --port 8001
```

The service will be available at `http://localhost:8001`

### 3. Test the endpoints

```bash
# Health check
curl http://localhost:8001/health

# Hello endpoint
curl http://localhost:8001/internal/hello
```

