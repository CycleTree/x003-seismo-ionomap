from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ObservationPriority:
    system: str = "G"
    l1_priority: tuple[str, ...] = ("L1C", "L1W", "L1P")
    l2_priority: tuple[str, ...] = ("L2W", "L2P", "L2L", "L2X")
    c1_priority: tuple[str, ...] = ("C1C", "C1W", "C1P")
    c2_priority: tuple[str, ...] = ("C2W", "C2P", "C2L", "C2X")
    s1_priority: tuple[str, ...] = ("S1C", "S1W", "S1P")
    s2_priority: tuple[str, ...] = ("S2W", "S2P", "S2L", "S2X")


@dataclass(frozen=True)
class IngestConfig:
    default_station_id: str | None = None
    observation_priority: ObservationPriority = field(default_factory=ObservationPriority)
