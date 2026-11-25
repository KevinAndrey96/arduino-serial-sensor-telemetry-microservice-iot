"""
Configuration settings for Arduino Serial Sensor Telemetry Microservice.
Loads configuration from environment variables with production defaults.
"""

import os

# Serial Hardware Settings
SERIAL_PORT = os.getenv("SERIAL_PORT", "auto")
BAUD_RATE = int(os.getenv("BAUD_RATE", "9600"))
SERIAL_TIMEOUT_SEC = float(os.getenv("SERIAL_TIMEOUT_SEC", "1.0"))

# Cloud / Backend Dispatch Settings
TELEMETRY_ENDPOINT = os.getenv("TELEMETRY_ENDPOINT", "http://127.0.0.1:8000/api/v1/telemetry")
DISPATCH_TIMEOUT_SEC = float(os.getenv("DISPATCH_TIMEOUT_SEC", "5.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "1.5"))

# Buffer & Store-and-Forward Settings
OFFLINE_BUFFER_MAX_SIZE = int(os.getenv("OFFLINE_BUFFER_MAX_SIZE", "1000"))
FLUSH_BATCH_SIZE = int(os.getenv("FLUSH_BATCH_SIZE", "20"))

# Simulator Settings
SIMULATOR_ENABLED = os.getenv("SIMULATOR_ENABLED", "false").lower() in ("true", "1", "yes")
SIMULATOR_INTERVAL_SEC = float(os.getenv("SIMULATOR_INTERVAL_SEC", "1.0"))

# Monitoring Web Server
WEB_SERVER_ENABLED = os.getenv("WEB_SERVER_ENABLED", "true").lower() in ("true", "1", "yes")
WEB_PORT = int(os.getenv("WEB_PORT", "8080"))
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
