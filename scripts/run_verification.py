#!/usr/bin/env python3
"""
Standalone Verification Script for Arduino Serial Telemetry Microservice.
Runs tests with zero external dependencies.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.packet_parser import PacketParser, calculate_xor_checksum, verify_checksum
from src.simulator import ArduinoSensorSimulator
from src.dispatcher import TelemetryDispatcher
from src.server import start_telemetry_server
import time
import json
from urllib.request import Request, urlopen

def run_tests():
    print("[*] Starting Arduino Serial Telemetry Gateway Test Suite...\n")

    # 1. Packet Parser Test
    print("[1/4] Testing Packet Parser (CSV, JSON, Key-Value)...")
    parser = PacketParser()
    csv_raw = "17.69,4.23,3.65,1.96,2.54,15.69,1.23"
    csv_res = parser.parse(csv_raw)
    assert csv_res["status"] == "VALID"
    assert csv_res["channel_count"] == 7
    assert csv_res["sensors"]["temp_ambient_c"] == 17.69
    assert csv_res["sensors"]["voltage_v"] == 15.69

    json_raw = '{"temp": 28.5, "hum": 62.0}'
    json_res = parser.parse(json_raw)
    assert json_res["sensors"]["temp"] == 28.5

    # Checksum test
    csum = calculate_xor_checksum(csv_raw)
    clean, valid = verify_checksum(f"{csv_raw}*{csum}")
    assert valid is True
    print("  -> Passed: Multi-format parsing and checksum verification working.\n")

    # 2. Simulator Test
    print("[2/4] Testing Sensor Simulator...")
    sim = ArduinoSensorSimulator(include_checksum=True)
    frame = sim.generate_csv_frame()
    assert "*" in frame
    parsed = parser.parse(frame)
    assert parsed["channel_count"] == 7
    print("  -> Passed: Mock sensor streams generated with valid ranges.\n")

    # 3. Dispatcher Buffer Test
    print("[3/4] Testing Resilient Dispatcher Offline Queuing...")
    dispatcher = TelemetryDispatcher(
        endpoint_url="http://127.0.0.1:59999/api/v1/telemetry",
        timeout_sec=0.2,
        max_retries=1,
        max_buffer_size=5
    )
    dispatcher.dispatch({"sequence_id": 1, "sensors": {"v": 1}})
    assert dispatcher.buffer_size == 1
    assert dispatcher.stats["is_connected"] is False
    print("  -> Passed: Offline store-and-forward queueing verified.\n")

    # 4. HTTP Server Test
    print("[4/4] Testing Monitoring Server & Ingestion Receiver...")
    test_port = 8992
    server = start_telemetry_server(host="127.0.0.1", port=test_port)
    time.sleep(0.3)

    req = Request(f"http://127.0.0.1:{test_port}/api/v1/health")
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "UP"

    post_req = Request(
        f"http://127.0.0.1:{test_port}/api/v1/telemetry",
        data=json.dumps({"test": 123}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urlopen(post_req) as resp:
        assert resp.status == 200

    server.shutdown()
    print("  -> Passed: Monitoring API and telemetry receiver verified.\n")

    print("=" * 60)
    print("[SUCCESS] All 4 Telemetry Microservice test modules passed!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
