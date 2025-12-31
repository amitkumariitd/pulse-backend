from contextlib import asynccontextmanager
from fastapi import FastAPI
from gapi.main import app as gapi_app
from pulse.main import app as pulse_app, lifespan as pulse_lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - initialize Pulse database pool."""
    # Start Pulse's lifespan (initializes database pool)
    async with pulse_lifespan(pulse_app):
        yield


app = FastAPI(
    title="Pulse Backend",
    description="Trading backend monorepo - single deployable (gapi + pulse)",
    lifespan=lifespan
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

