from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.anomaly import build_anomaly_router
from app.services.anomaly_grid import AnomalyGridServiceConfig


app = FastAPI(title="seismo-ionomap")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.11.114:5173",
        "http://192.168.11.8:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    build_anomaly_router(
        AnomalyGridServiceConfig(root_dir=Path("/data/intermediate")),
    )
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
