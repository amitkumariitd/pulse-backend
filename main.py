from fastapi import FastAPI
from services.gapi.main import app as gapi_app
from services.order_service.main import app as order_service_app

app = FastAPI(
    title="Pulse Backend",
    description="Trading backend monorepo with GAPI and Order Service"
)

app.mount("/gapi", gapi_app)
app.mount("/order_service", order_service_app)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "services": {
            "gapi": "mounted at /gapi",
            "order_service": "mounted at /order_service"
        }
    }

