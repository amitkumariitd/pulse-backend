from fastapi import FastAPI
from gapi.main import app as gapi_app
from pulse.main import app as pulse_app

app = FastAPI(
    title="Pulse Backend",
    description="Trading backend monorepo - single deployable (gapi + pulse)"
)

app.mount("/gapi", gapi_app)
app.mount("/pulse", pulse_app)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "components": {
            "gapi": "mounted at /gapi",
            "pulse": "mounted at /pulse"
        }
    }

