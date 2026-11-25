"""
Unit tests for Telemetry Packet Parser.
"""

import pytest
from src.packet_parser import (
    PacketParser,
    PacketParseError,
    calculate_xor_checksum,
    verify_checksum
)


def test_parse_csv_telemetry():
    parser = PacketParser()
    raw = "17.69,4.23,3.65,1.96,2.54,15.69,1.23"
    result = parser.parse(raw)

    assert result["status"] == "VALID"
    assert result["format"] == "csv"
    assert result["channel_count"] == 7
    assert result["sensors"]["temp_ambient_c"] == 17.69
    assert result["sensors"]["temp_chamber_c"] == 4.23
    assert result["sensors"]["humidity_pct"] == 3.65
    assert result["sensors"]["co2_ppm"] == 1.96
    assert result["sensors"]["pressure_kpa"] == 2.54
    assert result["sensors"]["voltage_v"] == 15.69
    assert result["sensors"]["current_a"] == 1.23
    assert result["sequence_id"] == 1


def test_parse_json_telemetry():
    parser = PacketParser()
    raw = '{"temperature": 25.4, "humidity": 60.1, "sensor_id": "DHT22"}'
    result = parser.parse(raw)

    assert result["status"] == "VALID"
    assert result["format"] == "json"
    assert result["sensors"]["temperature"] == 25.4
    assert result["sensors"]["humidity"] == 60.1
    assert result["sensors"]["sensor_id"] == "DHT22"


def test_parse_key_value_telemetry():
    parser = PacketParser()
    raw = "temp=21.5;hum=45.0;v_bat=12.4"
    result = parser.parse(raw)

    assert result["status"] == "VALID"
    assert result["format"] == "key_value"
    assert result["sensors"]["temp"] == 21.5
    assert result["sensors"]["hum"] == 45.0
    assert result["sensors"]["v_bat"] == 12.4


def test_xor_checksum():
    payload = "17.69,4.23,3.65"
    csum = calculate_xor_checksum(payload)
    assert len(csum) == 2
    assert csum == calculate_xor_checksum(payload)

    # Verify frame with valid checksum
    frame = f"{payload}*{csum}"
    clean_payload, is_valid = verify_checksum(frame)
    assert is_valid is True
    assert clean_payload == payload

    # Verify frame with corrupted checksum
    bad_frame = f"{payload}*FF"
    _, is_bad_valid = verify_checksum(bad_frame)
    assert is_bad_valid is False


def test_invalid_frames_raise_error():
    parser = PacketParser()
    with pytest.raises(PacketParseError):
        parser.parse("")

    with pytest.raises(PacketParseError):
        parser.parse("   ")

    with pytest.raises(PacketParseError):
        # Corrupted checksum
        parser.parse("17.69,4.23*00")
