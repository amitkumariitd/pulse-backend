from fastapi import FastAPI

app = FastAPI(title="GAPI")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from GAPI"}

