from __future__ import annotations

import numpy as np
import pandas as pd

from app.processing.bias import BiasProcessingConfig, apply_bias_components, estimate_bias_components


def test_bias_estimation_recovers_shared_receiver_and_satellite_structure() -> None:
    receiver_bias_true = {"STA1": 1.5, "STA2": -1.5}
    satellite_bias_true = {"G01": 2.0, "G02": -2.0}
    arc_bias_true = {
        "STA1:G01:0": 0.0,
        "STA1:G01:1": 0.0,
        "STA1:G02:0": 0.0,
        "STA2:G01:0": 0.0,
        "STA2:G02:0": 0.0,
        "STA2:G02:1": 0.0,
    }

    rows: list[dict[str, object]] = []
    for arc_id, arc_bias in arc_bias_true.items():
        station_id, sat_id, _ = arc_id.split(":")
        for second in (0, 30, 60):
            phase_stec = 10.0
            code_stec = phase_stec + receiver_bias_true[station_id] + satellite_bias_true[sat_id] + arc_bias
            rows.append(
                {
                    "station_id": station_id,
                    "sat_id": sat_id,
                    "arc_id": arc_id,
                    "time": pd.Timestamp("2026-05-20T00:00:00Z") + pd.Timedelta(seconds=second),
                    "phase_stec_tecu": phase_stec,
                    "code_stec_tecu": code_stec,
                }
            )

    frame = pd.DataFrame(rows)
    biases = estimate_bias_components(
        frame,
        BiasProcessingConfig(receiver_penalty=0.01, satellite_penalty=0.01, arc_penalty=10.0),
    )
    leveled = apply_bias_components(frame, biases)

    receiver = dict(zip(biases.receiver_biases["station_id"], biases.receiver_biases["receiver_bias_tecu"]))
    satellite = dict(zip(biases.satellite_biases["sat_id"], biases.satellite_biases["satellite_bias_tecu"]))

    assert np.isclose(receiver["STA1"], 1.5, atol=0.2)
    assert np.isclose(receiver["STA2"], -1.5, atol=0.2)
    assert np.isclose(satellite["G01"], 2.0, atol=0.2)
    assert np.isclose(satellite["G02"], -2.0, atol=0.2)
    assert np.allclose(leveled["bias_model_residual_tecu"], 0.0, atol=1e-6)
