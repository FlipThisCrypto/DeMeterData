# SPDX-License-Identifier: Apache-2.0
"""USB-serial talk to a Tree's provisioning console.

Each helper opens a fresh serial connection, sends a single command,
reads the line-oriented `OK ...` / `ERR ...` reply, and closes. No
persistent connection — keeps Flask request handling stateless.

Mirrors the command set in firmware/src/net/serial_console.{h,cpp}.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

import serial
import serial.tools.list_ports

from .config import settings

DEFAULT_BAUD = 115200


@dataclass
class PortInfo:
    device: str
    description: str
    hwid: str


class TreeError(RuntimeError):
    """Anything that goes wrong talking to a Tree."""


def list_ports() -> list[PortInfo]:
    """Enumerate every COM port pyserial can see."""
    return [
        PortInfo(p.device, p.description or "", p.hwid or "")
        for p in serial.tools.list_ports.comports()
    ]


def _open(port: str) -> serial.Serial:
    try:
        s = serial.Serial(
            port=port,
            baudrate=DEFAULT_BAUD,
            timeout=settings().serial_timeout,
            write_timeout=settings().serial_timeout,
        )
    except serial.SerialException as e:
        raise TreeError(f"could not open {port}: {e}") from e
    # Drain anything the Tree was already printing (e.g. periodic
    # sensor logs) so our request/response stays in sync.
    s.reset_input_buffer()
    return s


def _send_and_read_line(port: str, cmd: str, drain_extra: float = 0.05) -> str:
    """Send `cmd\\n`, read one line back. Return the line stripped."""
    with _open(port) as s:
        s.write((cmd + "\n").encode("utf-8"))
        s.flush()
        deadline = time.time() + settings().serial_timeout
        while time.time() < deadline:
            line = s.readline().decode("utf-8", errors="replace").strip()
            if line:
                # Skip background log lines that don't look like a response.
                if line.startswith("OK ") or line.startswith("OK") or line.startswith("ERR"):
                    return line
        raise TreeError(f"no response from {port} to {cmd!r}")


def ping(port: str) -> bool:
    line = _send_and_read_line(port, "PING")
    return line.startswith("OK")


def get_node_id(port: str) -> str:
    line = _send_and_read_line(port, "NODE_ID")
    if not line.startswith("OK "):
        raise TreeError(f"NODE_ID: {line}")
    return line[3:].strip()


def get_signing_key(port: str) -> str:
    line = _send_and_read_line(port, "KEY")
    if not line.startswith("OK "):
        raise TreeError(f"KEY: {line}")
    return line[3:].strip()


def get_status(port: str) -> dict:
    line = _send_and_read_line(port, "STATUS")
    if not line.startswith("OK "):
        raise TreeError(f"STATUS: {line}")
    payload = line[3:].strip()
    try:
        return json.loads(payload)
    except json.JSONDecodeError as e:
        raise TreeError(f"STATUS payload not JSON: {payload!r} ({e})") from e


def set_wifi(port: str, ssid: str, password: str) -> None:
    if " " in ssid:
        # The simple v1 command parser splits on the first space; SSIDs
        # with spaces aren't supported until we add a quoted form.
        raise TreeError("SSID cannot contain spaces in v1")
    line = _send_and_read_line(port, f"WIFI_SET {ssid} {password}")
    if not line.startswith("OK"):
        raise TreeError(f"WIFI_SET: {line}")


def set_oracle_url(port: str, url: str) -> None:
    line = _send_and_read_line(port, f"ORACLE_SET {url}")
    if not line.startswith("OK"):
        raise TreeError(f"ORACLE_SET: {line}")


def sample_now(port: str) -> None:
    line = _send_and_read_line(port, "SAMPLE_NOW")
    if not line.startswith("OK"):
        raise TreeError(f"SAMPLE_NOW: {line}")
