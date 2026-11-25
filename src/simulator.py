"""
Hardware Mock Simulator for Arduino Sensor Nodes.
Generates realistic environmental and electrical telemetry frames for testing without physical USB hardware.
"""

import math
import random
import time
from typing import Generator, Dict, Any
from .packet_parser import calculate_xor_checksum


class ArduinoSensorSimulator:
    """Simulates physical sensors attached to an Arduino Uno/Mega."""

    def __init__(self, include_checksum: bool = False):
        self.include_checksum = include_checksum
        self._step = 0
        # Baseline sensor states
        self.base_temp_ambient = 22.5
        self.base_temp_chamber = 37.5
        self.base_humidity = 60.0
        self.base_co2 = 450.0
        self.base_pressure = 101.3
        self.base_voltage = 12.0
        self.base_current = 1.25

    def generate_reading(self) -> Dict[str, float]:
        """Generates dynamic reading with smooth sinusoidal drift and random sensor jitter."""
        self._step += 1
        drift = math.sin(self._step / 10.0)

        temp_ambient = round(self.base_temp_ambient + (drift * 2.0) + random.uniform(-0.15, 0.15), 2)
        temp_chamber = round(self.base_temp_chamber + (math.cos(self._step / 15.0) * 0.5) + random.uniform(-0.05, 0.05), 2)
        humidity = round(max(10.0, min(95.0, self.base_humidity + (drift * 5.0) + random.uniform(-0.5, 0.5))), 2)
        co2 = round(max(350.0, self.base_co2 + (drift * 35.0) + random.uniform(-5.0, 5.0)), 1)
        pressure = round(self.base_pressure + (drift * 0.4) + random.uniform(-0.02, 0.02), 2)
        voltage = round(self.base_voltage + random.uniform(-0.08, 0.08), 2)
        current = round(max(0.1, self.base_current + (drift * 0.15) + random.uniform(-0.02, 0.02)), 2)

        return {
            "temp_ambient_c": temp_ambient,
            "temp_chamber_c": temp_chamber,
            "humidity_pct": humidity,
            "co2_ppm": co2,
            "pressure_kpa": pressure,
            "voltage_v": voltage,
            "current_a": current
        }

    def generate_csv_frame(self) -> str:
        """
        Formats reading into standard comma-separated array string:
        '17.69,4.23,3.65,1.96,2.54,15.69,1.23'
        """
        r = self.generate_reading()
        raw = f"{r['temp_ambient_c']},{r['temp_chamber_c']},{r['humidity_pct']},{r['co2_ppm']},{r['pressure_kpa']},{r['voltage_v']},{r['current_a']}"
        if self.include_checksum:
            csum = calculate_xor_checksum(raw)
            return f"{raw}*{csum}"
        return raw

    def stream_frames(self, interval_sec: float = 1.0) -> Generator[str, None, None]:
        """Infinite generator yielding periodic telemetry frames."""
        while True:
            yield self.generate_csv_frame()
            time.sleep(interval_sec)
