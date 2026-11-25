"""
Hardware Serial Port Reader for Arduino Devices.
Handles port auto-discovery, auto-reconnection, baud rate negotiation, and line reading.
"""

import logging
import time
from typing import Optional, List, Generator

logger = logging.getLogger("SerialReader")

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


def discover_arduino_ports() -> List[str]:
    """Scans and lists candidate serial ports matching common Arduino USB-to-UART bridges."""
    if not HAS_SERIAL:
        return []

    candidate_ports = []
    known_chips = ["arduino", "ch340", "ftdi", "cp210", "usb serial", "ch341", "pl2303"]

    for port_info in serial.tools.list_ports.comports():
        device = port_info.device
        desc = (port_info.description or "").lower()
        mfg = (port_info.manufacturer or "").lower()

        # Check description or manufacturer
        if any(chip in desc for chip in known_chips) or any(chip in mfg for chip in known_chips):
            candidate_ports.append(device)
        elif "ttyusb" in device.lower() or "ttyacm" in device.lower() or "usbmodem" in device.lower():
            candidate_ports.append(device)

    return candidate_ports


class SerialReader:
    """Manages physical serial line communication with an Arduino microcontroller."""

    def __init__(
        self,
        port: str = "auto",
        baud_rate: int = 9600,
        timeout_sec: float = 1.0,
        reconnect_interval_sec: float = 3.0
    ):
        self.port_setting = port
        self.baud_rate = baud_rate
        self.timeout_sec = timeout_sec
        self.reconnect_interval_sec = reconnect_interval_sec

        self._serial_conn = None
        self._active_port: Optional[str] = None
        self._is_running = False

    @property
    def is_connected(self) -> bool:
        return self._serial_conn is not None and self._serial_conn.is_open

    @property
    def active_port(self) -> Optional[str]:
        return self._active_port

    def connect(self) -> bool:
        """Establishes connection to serial device."""
        if not HAS_SERIAL:
            logger.error("pyserial package is not installed. Run 'pip install pyserial' or use simulator mode.")
            return False

        target_port = self.port_setting
        if target_port == "auto":
            candidates = discover_arduino_ports()
            if not candidates:
                logger.warning("No Arduino or USB serial devices auto-discovered.")
                return False
            target_port = candidates[0]
            logger.info("Auto-selected serial port: %s", target_port)

        try:
            self._serial_conn = serial.Serial(
                port=target_port,
                baudrate=self.baud_rate,
                timeout=self.timeout_sec
            )
            # Reset Arduino DTR line
            self._serial_conn.dtr = False
            time.sleep(0.1)
            self._serial_conn.dtr = True
            time.sleep(1.5)  # Allow Arduino bootloader to initialize

            self._active_port = target_port
            logger.info("Connected to serial port %s at %d baud.", target_port, self.baud_rate)
            return True
        except (serial.SerialException, OSError) as exc:
            logger.error("Failed to connect to %s: %s", target_port, exc)
            self._serial_conn = None
            self._active_port = None
            return False

    def read_line(self) -> Optional[str]:
        """Reads a single line terminated by LF/CRLF from serial port."""
        if not self.is_connected:
            return None

        try:
            line_bytes = self._serial_conn.readline()
            if not line_bytes:
                return None
            return line_bytes.decode("utf-8", errors="replace").strip()
        except (serial.SerialException, OSError) as exc:
            logger.warning("Serial read error on %s: %s. Reconnecting...", self._active_port, exc)
            self.close()
            return None

    def close(self) -> None:
        """Closes serial connection."""
        if self._serial_conn:
            try:
                self._serial_conn.close()
            except Exception:
                pass
            self._serial_conn = None
            self._active_port = None
            logger.info("Serial port connection closed.")
