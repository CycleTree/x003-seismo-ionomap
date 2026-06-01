from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ObservationPriority:
    system: str
    l1_priority: tuple[str, ...]
    l2_priority: tuple[str, ...]
    c1_priority: tuple[str, ...]
    c2_priority: tuple[str, ...]
    s1_priority: tuple[str, ...]
    s2_priority: tuple[str, ...]


def default_observation_priorities() -> tuple[ObservationPriority, ...]:
    return (
        ObservationPriority(
            system="G",
            l1_priority=("L1C", "L1W", "L1P"),
            l2_priority=("L2W", "L2P", "L2L", "L2X"),
            c1_priority=("C1C", "C1W", "C1P"),
            c2_priority=("C2W", "C2P", "C2L", "C2X"),
            s1_priority=("S1C", "S1W", "S1P"),
            s2_priority=("S2W", "S2P", "S2L", "S2X"),
        ),
        ObservationPriority(
            system="R",
            l1_priority=("L1C", "L1P"),
            l2_priority=("L2C", "L2P"),
            c1_priority=("C1C", "C1P"),
            c2_priority=("C2C", "C2P"),
            s1_priority=("S1C", "S1P"),
            s2_priority=("S2C", "S2P"),
        ),
        ObservationPriority(
            system="E",
            l1_priority=("L1X", "L1C", "L1B"),
            l2_priority=("L5X", "L5Q", "L5I"),
            c1_priority=("C1X", "C1C", "C1B"),
            c2_priority=("C5X", "C5Q", "C5I"),
            s1_priority=("S1X", "S1C", "S1B"),
            s2_priority=("S5X", "S5Q", "S5I"),
        ),
        ObservationPriority(
            system="J",
            l1_priority=("L1C", "L1X"),
            l2_priority=("L2X", "L2L", "L2S"),
            c1_priority=("C1C", "C1X"),
            c2_priority=("C2X", "C2L", "C2S"),
            s1_priority=("S1C", "S1X"),
            s2_priority=("S2X", "S2L", "S2S"),
        ),
    )


@dataclass(frozen=True)
class IngestConfig:
    default_station_id: str | None = None
    observation_priorities: tuple[ObservationPriority, ...] = field(default_factory=default_observation_priorities)
