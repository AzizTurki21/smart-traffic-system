from __future__ import annotations

import logging
from typing import Protocol

from .config import LANES, PINS

log = logging.getLogger(__name__)


class SignalOutput(Protocol):
    def set_states(self, states: dict[str, str]) -> None: ...
    def close(self) -> None: ...


class ConsoleOutput:
    def set_states(self, states: dict[str, str]) -> None:
        log.info("Signals: %s", states)

    def close(self) -> None:
        pass


class GpioOutput:
    """BCM GPIO output using gpiozero. Keep GPIO disabled until wiring is checked."""

    def __init__(self) -> None:
        from gpiozero import LED

        self.leds = {
            lane: {
                "green": LED(PINS[lane].green),
                "red": LED(PINS[lane].red),
                "yellow": LED(PINS[lane].yellow),
            }
            for lane in LANES
        }
        self.set_states({lane: "red" for lane in LANES})

    def set_states(self, states: dict[str, str]) -> None:
        for lane, colors in self.leds.items():
            active = states.get(lane, "red")
            for color, led in colors.items():
                led.on() if color == active else led.off()

    def close(self) -> None:
        for colors in self.leds.values():
            for led in colors.values():
                led.off()
                led.close()
