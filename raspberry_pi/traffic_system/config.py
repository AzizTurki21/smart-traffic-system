from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LanePins:
    green: int
    red: int
    yellow: int


LANES = ("lane1", "lane2", "lane3")
PINS = {
    "lane1": LanePins(green=22, red=17, yellow=27),
    "lane2": LanePins(green=23, red=25, yellow=24),
    "lane3": LanePins(green=5, red=26, yellow=6),
}


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def camera_map() -> list[tuple[int, str]]:
    raw = os.getenv("CAMERAS", "0:lane1,1:lane2,2:lane3")
    result: list[tuple[int, str]] = []
    for item in raw.split(","):
        index, lane = item.strip().split(":", 1)
        if lane not in LANES:
            raise ValueError(f"Unsupported lane in CAMERAS: {lane}")
        result.append((int(index), lane))
    if not result:
        raise ValueError("CAMERAS must include at least one index:lane pair")
    return result
