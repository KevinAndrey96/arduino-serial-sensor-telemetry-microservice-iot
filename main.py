#!/usr/bin/env python3
"""
Arduino Serial Sensor Telemetry Microservice IoT.
CLI Entrypoint and Service Daemon.
"""

import argparse
import logging
import os
import sys

from src.config import (
    SERIAL_PORT,
    BAUD_RATE,
    TELEMETRY_ENDPOINT,
    SIMULATOR_ENABLED,
    WEB_SERVER_ENABLED,
    WEB_PORT,
    WEB_HOST,
    LOG_LEVEL
)
from src.gateway import IoTTelemetryGateway


def setup_logging(level_name: str):
    """Configures structured console logging."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Arduino Serial Sensor Telemetry Microservice IoT - Edge-to-Cloud Gateway"
    )
    parser.add_argument(
        "--port",
        default=SERIAL_PORT,
        help="Serial port (e.g., /dev/ttyUSB0, COM3, or 'auto' for auto-detection)"
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=BAUD_RATE,
        help=f"Serial baud rate (default: {BAUD_RATE})"
    )
    parser.add_argument(
        "--endpoint",
        default=TELEMETRY_ENDPOINT,
        help=f"Target HTTP telemetry ingest endpoint (default: {TELEMETRY_ENDPOINT})"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        default=SIMULATOR_ENABLED,
        help="Run in mock hardware simulation mode (generates dynamic multi-sensor telemetry)"
    )
    parser.add_argument(
        "--web",
        action="store_true",
        default=WEB_SERVER_ENABLED,
        help="Enable embedded monitoring HTTP dashboard & local telemetry receiver"
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=WEB_PORT,
        help=f"Port for embedded monitoring dashboard (default: {WEB_PORT})"
    )
    parser.add_argument(
        "--web-host",
        default=WEB_HOST,
        help=f"Host interface for embedded monitoring dashboard (default: {WEB_HOST})"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Telemetry acquisition and dispatch interval in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--log-level",
        default=LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log verbosity level"
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    gateway = IoTTelemetryGateway(
        endpoint_url=args.endpoint,
        serial_port=args.port,
        baud_rate=args.baud,
        simulate=args.simulate,
        poll_interval_sec=args.interval,
        enable_web=args.web,
        web_port=args.web_port,
        web_host=args.web_host
    )

    gateway.start()


if __name__ == "__main__":
    main()
