from fastapi import FastAPI

app = FastAPI(title="Order Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/internal/hello")
def hello():
    return {"message": "Hello from Order Service"}

