"""
Telemetry Packet Parser for Arduino Serial Sensor Streams.
Supports CSV arrays, JSON objects, and Key-Value formatted frames with checksum verification.
"""

import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple


# Default sensor channel mapping for standard 7-channel Arduino telemetry arrays
DEFAULT_SENSOR_CHANNELS = [
    "temp_ambient_c",
    "temp_chamber_c",
    "humidity_pct",
    "co2_ppm",
    "pressure_kpa",
    "voltage_v",
    "current_a"
]


class PacketParseError(Exception):
    """Raised when an incoming serial frame is malformed or fails validation."""
    pass


def calculate_xor_checksum(payload: str) -> str:
    """Calculate simple 2-hex-digit XOR checksum (NMEA 0183 standard)."""
    csum = 0
    for char in payload:
        csum ^= ord(char)
    return f"{csum:02X}"


def verify_checksum(raw_line: str) -> Tuple[str, bool]:
    """
    Checks if frame contains an asterisk checksum (e.g. 'payload*2F').
    Returns (clean_payload, is_valid).
    If no checksum is present, returns (raw_line, True).
    """
    if "*" in raw_line:
        parts = raw_line.rsplit("*", 1)
        payload = parts[0]
        expected = parts[1].strip().upper()
        actual = calculate_xor_checksum(payload)
        return payload, actual == expected
    return raw_line, True


class PacketParser:
    """Parses raw serial strings into structured telemetry payloads."""

    def __init__(self, channel_names: Optional[List[str]] = None):
        self.channel_names = channel_names or DEFAULT_SENSOR_CHANNELS
        self._sequence_counter = 0

    def parse(self, raw_line: str) -> Dict[str, Any]:
        """
        Parses a raw line received from Arduino serial buffer into a structured dict.
        """
        if not raw_line or not isinstance(raw_line, str):
            raise PacketParseError("Empty or invalid line buffer.")

        cleaned = raw_line.strip()
        if not cleaned:
            raise PacketParseError("Blank line after trimming.")

        # Check for NMEA-style checksum if present
        payload, checksum_valid = verify_checksum(cleaned)
        if not checksum_valid:
            raise PacketParseError(f"Checksum mismatch on frame: {cleaned}")

        self._sequence_counter += 1
        now_utc = datetime.now(timezone.utc).isoformat()

        # 1. Try JSON format
        if payload.startswith("{") and payload.endswith("}"):
            try:
                data = json.loads(payload)
                return {
                    "sequence_id": self._sequence_counter,
                    "timestamp": now_utc,
                    "format": "json",
                    "raw_payload": payload,
                    "sensors": data,
                    "status": "VALID"
                }
            except json.JSONDecodeError as exc:
                raise PacketParseError(f"Invalid JSON packet: {exc}")

        # 2. Try Key-Value format (e.g. "temp=21.5;hum=45.0")
        if "=" in payload and (";" in payload or "&" in payload):
            delimiter = ";" if ";" in payload else "&"
            sensors = {}
            for item in payload.split(delimiter):
                if "=" in item:
                    k, v = item.split("=", 1)
                    k = k.strip()
                    try:
                        sensors[k] = float(v.strip())
                    except ValueError:
                        sensors[k] = v.strip()
            return {
                "sequence_id": self._sequence_counter,
                "timestamp": now_utc,
                "format": "key_value",
                "raw_payload": payload,
                "sensors": sensors,
                "status": "VALID"
            }

        # 3. Standard CSV Array (e.g. "17.69,4.23,3.65,1.96,2.54,15.69,1.23")
        parts = [p.strip() for p in payload.split(",") if p.strip()]
        if not parts:
            raise PacketParseError("No valid tokens found in CSV frame.")

        sensors = {}
        for idx, token in enumerate(parts):
            channel = self.channel_names[idx] if idx < len(self.channel_names) else f"channel_{idx + 1}"
            try:
                val = float(token)
                sensors[channel] = val
            except ValueError:
                sensors[channel] = token

        return {
            "sequence_id": self._sequence_counter,
            "timestamp": now_utc,
            "format": "csv",
            "raw_payload": payload,
            "sensors": sensors,
            "channel_count": len(sensors),
            "status": "VALID"
        }
