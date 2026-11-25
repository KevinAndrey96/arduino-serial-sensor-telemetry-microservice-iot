"""
Unit tests for Monitoring Server and Local Ingestion Receiver.
"""

import json
import time
from urllib.request import Request, urlopen
from src.server import start_telemetry_server, global_telemetry_state


def test_server_health_and_telemetry_flow():
    # Spawn server on test port
    test_port = 8991
    server = start_telemetry_server(host="127.0.0.1", port=test_port)
    time.sleep(0.2)

    # 1. Healthcheck
    req = Request(f"http://127.0.0.1:{test_port}/api/v1/health")
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "UP"

    # 2. Ingest Telemetry Frame
    payload = json.dumps({"sensor_a": 12.3, "sensor_b": 45.6}).encode("utf-8")
    post_req = Request(
        f"http://127.0.0.1:{test_port}/api/v1/telemetry",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urlopen(post_req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "success"

    # 3. Check Metrics
    metrics_req = Request(f"http://127.0.0.1:{test_port}/api/v1/metrics")
    with urlopen(metrics_req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "success"

    server.shutdown()
