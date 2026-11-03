from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Callable

from .config import LANES
from .hardware import SignalOutput

log = logging.getLogger(__name__)


@dataclass
class Phase:
    mode: str
    lane: str
    color: str
    duration: float


class TrafficController:
    """Three-approach signal cycle and priority-event state machine."""

    def __init__(self, output: SignalOutput, publish: Callable[[str], None] | None,
                 green_seconds: int = 7, yellow_seconds: int = 3,
                 priority_seconds: int = 12) -> None:
        self.output = output
        self.publish = publish
        self.green_seconds = green_seconds
        self.yellow_seconds = yellow_seconds
        self.priority_seconds = priority_seconds
        self.cycle_index = 0
        self.priority_lane: str | None = None
        self.priority_until = 0.0
        self.phase_started = time.monotonic()
        self.last_publish = 0.0
        self.phase = Phase("normal", LANES[0], "green", green_seconds)
        self.states = {lane: "red" for lane in LANES}
        self._apply()

    def on_detection(self, raw_payload: bytes | str) -> None:
        try:
            data = json.loads(raw_payload)
            lane = data.get("lane")
            confidence = float(data.get("confidence", 1.0))
            class_name = str(data.get("class", "")).strip().lower()
            allowed = {name.strip().lower() for name in __import__("os").getenv(
                "PRIORITY_CLASSES", "ambulance,police,fire_truck"
            ).split(",")}
            if lane not in LANES or class_name not in allowed or not 0 <= confidence <= 1:
                log.warning("Ignoring unsupported detection event: %s", data)
                return
            self.priority_lane = lane
            self.priority_until = time.monotonic() + self.priority_seconds
            self.phase_started = time.monotonic()
            self.phase = Phase("priority", lane, "green", self.priority_seconds)
            log.info("Priority vehicle (%s) assigned to %s", class_name, lane)
            self._apply()
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            log.warning("Ignoring malformed detection payload: %s", exc)

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        elapsed = now - self.phase_started

        if self.priority_lane:
            if now < self.priority_until:
                if self.phase.color != "green":
                    self.phase = Phase("priority", self.priority_lane, "green", self.priority_seconds)
                    self.phase_started = now
                    self._apply()
            else:
                self.priority_lane = None
                self.cycle_index = LANES.index(self.phase.lane)
                self._next_normal_phase(now)
        elif elapsed >= self.phase.duration:
            self._next_normal_phase(now)

        if self.publish and now - self.last_publish >= 1.0:
            self.publish(self.state_payload(now))
            self.last_publish = now

    def _next_normal_phase(self, now: float) -> None:
        if self.phase.color == "green":
            lane = LANES[self.cycle_index]
            self.phase = Phase("normal", lane, "yellow", self.yellow_seconds)
        else:
            self.cycle_index = (self.cycle_index + 1) % len(LANES)
            lane = LANES[self.cycle_index]
            self.phase = Phase("normal", lane, "green", self.green_seconds)
        self.phase_started = now
        self._apply()

    def _apply(self) -> None:
        self.states = {lane: "red" for lane in LANES}
        self.states[self.phase.lane] = self.phase.color
        self.output.set_states(self.states)

    def state_payload(self, now: float | None = None) -> str:
        now = time.monotonic() if now is None else now
        remaining = max(0, int(self.phase.duration - (now - self.phase_started) + 0.999))
        return json.dumps({
            "mode": self.phase.mode,
            "active_lane": self.phase.lane,
            "remaining_s": remaining,
            "lanes": self.states,
            "timestamp": time.time(),
        }, separators=(",", ":"))
