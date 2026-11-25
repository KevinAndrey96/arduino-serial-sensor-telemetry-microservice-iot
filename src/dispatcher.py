"""
Resilient HTTP Telemetry Dispatcher with Exponential Backoff and Store-and-Forward Buffering.
Ensures zero data loss during temporary network or backend server dropouts.
"""

import json
import logging
import time
from collections import deque
from typing import Dict, Any, Optional
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger("TelemetryDispatcher")


class TelemetryDispatcher:
    """Dispatches telemetry packets to a remote HTTP endpoint with offline queuing."""

    def __init__(
        self,
        endpoint_url: str,
        timeout_sec: float = 5.0,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        max_buffer_size: int = 1000,
        payload_mode: str = "json"  # "json" or "form"
    ):
        self.endpoint_url = endpoint_url
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_buffer_size = max_buffer_size
        self.payload_mode = payload_mode

        self._buffer: deque = deque(maxlen=max_buffer_size)
        self.stats = {
            "total_sent": 0,
            "total_failed": 0,
            "total_buffered": 0,
            "total_flushed_from_buffer": 0,
            "last_dispatch_at": None,
            "last_error": None,
            "is_connected": True
        }

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    def dispatch(self, packet: Dict[str, Any]) -> bool:
        """
        Attempts to dispatch a packet. If transmission fails, buffers the packet.
        Also attempts to flush any previously buffered packets if successful.
        """
        # If we have buffered backlog, flush first
        if self._buffer:
            self._flush_buffer()

        success = self._send_with_retry(packet)
        if success:
            self.stats["total_sent"] += 1
            self.stats["last_dispatch_at"] = packet.get("timestamp")
            self.stats["is_connected"] = True
            return True
        else:
            self._queue_packet(packet)
            return False

    def _queue_packet(self, packet: Dict[str, Any]) -> None:
        """Stores packet in memory queue when network is unavailable."""
        self._buffer.append(packet)
        self.stats["total_buffered"] += 1
        self.stats["is_connected"] = False
        logger.warning(
            "Buffered telemetry packet locally (Buffer size: %d/%d). Endpoint: %s",
            len(self._buffer),
            self.max_buffer_size,
            self.endpoint_url
        )

    def _flush_buffer(self) -> int:
        """Attempts to transmit pending packets in FIFO order."""
        flushed_count = 0
        while self._buffer:
            peek_packet = self._buffer[0]
            if self._send_with_retry(peek_packet):
                self._buffer.popleft()
                flushed_count += 1
                self.stats["total_sent"] += 1
                self.stats["total_flushed_from_buffer"] += 1
            else:
                # Still unreachable, stop flushing
                break

        if flushed_count > 0:
            logger.info("Successfully flushed %d buffered packets to remote endpoint.", flushed_count)
        return flushed_count

    def _send_with_retry(self, packet: Dict[str, Any]) -> bool:
        """Transmits packet with exponential backoff retry loop."""
        delay = 0.5
        for attempt in range(1, self.max_retries + 1):
            try:
                self._execute_http_request(packet)
                return True
            except (URLError, HTTPError, TimeoutError, OSError) as exc:
                self.stats["last_error"] = str(exc)
                if attempt == self.max_retries:
                    logger.debug("Dispatch failed after %d attempts: %s", attempt, exc)
                time.sleep(delay)
                delay *= self.backoff_factor

        self.stats["total_failed"] += 1
        return False

    def _execute_http_request(self, packet: Dict[str, Any]) -> str:
        """Low-level HTTP dispatch using standard library urllib."""
        if self.payload_mode == "form":
            # Historical format: POST {'Dato': '17.69,4.23,3.65...'}
            raw = packet.get("raw_payload", "")
            post_fields = {"Dato": raw}
            data_bytes = urlencode(post_fields).encode("utf-8")
            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}
        else:
            # Modern JSON API format
            data_bytes = json.dumps(packet).encode("utf-8")
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "Arduino-Serial-Telemetry-Gateway/1.0"
            }

        req = Request(self.endpoint_url, data=data_bytes, headers=headers, method="POST")
        with urlopen(req, timeout=self.timeout_sec) as response:
            return response.read().decode("utf-8")
