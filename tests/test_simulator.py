"""
Unit tests for Hardware Mock Simulator.
"""

from src.simulator import ArduinoSensorSimulator
from src.packet_parser import PacketParser


def test_simulator_reading_structure():
    sim = ArduinoSensorSimulator()
    reading = sim.generate_reading()

    assert "temp_ambient_c" in reading
    assert "temp_chamber_c" in reading
    assert "humidity_pct" in reading
    assert "co2_ppm" in reading
    assert "pressure_kpa" in reading
    assert "voltage_v" in reading
    assert "current_a" in reading

    assert 15.0 <= reading["temp_ambient_c"] <= 30.0
    assert 30.0 <= reading["temp_chamber_c"] <= 45.0
    assert 10.0 <= reading["humidity_pct"] <= 95.0
    assert 350.0 <= reading["co2_ppm"] <= 600.0


def test_simulator_csv_generation():
    sim = ArduinoSensorSimulator(include_checksum=True)
    frame = sim.generate_csv_frame()

    assert "*" in frame
    parser = PacketParser()
    parsed = parser.parse(frame)
    assert parsed["status"] == "VALID"
    assert parsed["channel_count"] == 7
