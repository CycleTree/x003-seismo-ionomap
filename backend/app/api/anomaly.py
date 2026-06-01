from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.anomaly_grid import (
    AnomalyGridServiceConfig,
    anomaly_grid_to_geojson,
    filter_grid_by_time,
    list_available_times,
    load_anomaly_grid,
)


def build_anomaly_router(config: AnomalyGridServiceConfig) -> APIRouter:
    router = APIRouter(prefix="/api/anomaly-grid", tags=["anomaly-grid"])

    @router.get("/times")
    def get_available_times() -> dict[str, object]:
        try:
            frame = load_anomaly_grid(config)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"times": list_available_times(frame)}

    @router.get("")
    def get_anomaly_grid(time: str | None = Query(default=None)) -> dict[str, object]:
        try:
            frame = load_anomaly_grid(config)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        filtered, resolved_time = filter_grid_by_time(frame, time)
        if filtered.empty:
            raise HTTPException(status_code=404, detail=f"No anomaly grid rows found for time={resolved_time}")
        return {
            "time": resolved_time,
            "featureCollection": anomaly_grid_to_geojson(filtered),
            "stats": {
                "cellCount": int(len(filtered)),
                "maxAbsZScore": float(filtered["abs_z_score"].max()),
                "meanZScore": float(filtered["z_score"].mean()),
            },
        }

    return router
