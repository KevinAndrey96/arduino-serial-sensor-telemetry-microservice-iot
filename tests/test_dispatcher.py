"""
Unit tests for Resilient Telemetry Dispatcher and Store-and-Forward Queuing.
"""

from src.dispatcher import TelemetryDispatcher


def test_dispatcher_offline_buffering():
    # Target an unreachable port to test offline buffering
    dispatcher = TelemetryDispatcher(
        endpoint_url="http://127.0.0.1:59999/api/v1/telemetry",
        timeout_sec=0.2,
        max_retries=1,
        max_buffer_size=5
    )

    packet = {
        "sequence_id": 1,
        "timestamp": "2026-11-24T20:00:00Z",
        "sensors": {"temp": 24.5}
    }

    # Dispatch should fail and queue packet
    success = dispatcher.dispatch(packet)
    assert success is False
    assert dispatcher.buffer_size == 1
    assert dispatcher.stats["total_buffered"] == 1
    assert dispatcher.stats["is_connected"] is False


def test_dispatcher_buffer_limit():
    dispatcher = TelemetryDispatcher(
        endpoint_url="http://127.0.0.1:59999/api/v1/telemetry",
        timeout_sec=0.1,
        max_retries=1,
        max_buffer_size=3
    )

    for i in range(5):
        dispatcher.dispatch({"sequence_id": i, "sensors": {"val": i}})

    # Buffer should not exceed max_buffer_size
    assert dispatcher.buffer_size == 3
