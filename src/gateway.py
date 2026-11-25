"""
Main IoT Telemetry Gateway Orchestrator.
Coordinates serial reading (or simulation), packet parsing, store-and-forward dispatching,
and monitoring server updates.
"""

import logging
import signal
import sys
import time
from typing import Optional

from .packet_parser import PacketParser, PacketParseError
from .dispatcher import TelemetryDispatcher
from .serial_reader import SerialReader, discover_arduino_ports
from .simulator import ArduinoSensorSimulator
from .server import global_telemetry_state, start_telemetry_server

logger = logging.getLogger("IoTGateway")


class IoTTelemetryGateway:
    """Central gateway connecting Arduino sensors to cloud backends."""

    def __init__(
        self,
        endpoint_url: str = "http://127.0.0.1:8080/api/v1/telemetry",
        serial_port: str = "auto",
        baud_rate: int = 9600,
        simulate: bool = False,
        poll_interval_sec: float = 1.0,
        enable_web: bool = True,
        web_port: int = 8080,
        web_host: str = "0.0.0.0"
    ):
        self.endpoint_url = endpoint_url
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.simulate = simulate
        self.poll_interval_sec = poll_interval_sec
        self.enable_web = enable_web
        self.web_port = web_port
        self.web_host = web_host

        self.parser = PacketParser()
        self.dispatcher = TelemetryDispatcher(endpoint_url=endpoint_url)
        self.simulator = ArduinoSensorSimulator() if simulate else None
        self.reader = SerialReader(port=serial_port, baud_rate=baud_rate) if not simulate else None

        self._running = False
        self._server = None

    def start(self):
        """Starts gateway telemetry acquisition loop."""
        self._running = True

        # Start monitoring HTTP server if enabled
        if self.enable_web:
            try:
                self._server = start_telemetry_server(self.web_host, self.web_port)
            except OSError as e:
                logger.warning("Could not bind monitoring server on port %d: %s. Continuing...", self.web_port, e)

        logger.info("=" * 60)
        logger.info("Starting Arduino Serial Sensor Telemetry Gateway")
        logger.info("Mode: %s", "MOCK SIMULATOR" if self.simulate else f"HARDWARE SERIAL ({self.serial_port} @ {self.baud_rate})")
        logger.info("Dispatch Destination: %s", self.endpoint_url)
        logger.info("=" * 60)

        if not self.simulate:
            connected = self.reader.connect()
            if not connected:
                logger.warning("Could not open serial port initially. Retrying during execution loop...")

        try:
            while self._running:
                raw_frame = self._acquire_next_frame()

                if raw_frame:
                    try:
                        packet = self.parser.parse(raw_frame)
                        global_telemetry_state.update_latest(packet)

                        # Dispatch packet
                        dispatched = self.dispatcher.dispatch(packet)

                        # Update shared stats
                        stats = dict(self.dispatcher.stats)
                        stats["buffer_size"] = self.dispatcher.buffer_size
                        stats["mode"] = "simulation" if self.simulate else "serial"
                        global_telemetry_state.update_gateway_stats(stats)

                        logger.debug("Telemetry processed: seq=%d, dispatched=%s", packet.get("sequence_id"), dispatched)
                    except PacketParseError as pe:
                        logger.warning("Discarded malformed frame: %s (%s)", raw_frame, pe)

                time.sleep(self.poll_interval_sec)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Shutting down gateway...")
        finally:
            self.stop()

    def _acquire_next_frame(self) -> Optional[str]:
        """Fetches raw frame from simulator or physical serial port."""
        if self.simulate:
            return self.simulator.generate_csv_frame()

        if not self.reader.is_connected:
            self.reader.connect()
            return None

        return self.reader.read_line()

    def stop(self):
        """Stops the gateway and releases resources."""
        self._running = False
        if self.reader:
            self.reader.close()
        logger.info("Arduino Telemetry Gateway stopped cleanly.")
