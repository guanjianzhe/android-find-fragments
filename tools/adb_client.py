"""ADB client for executing commands and parsing Android device information."""

import re
import subprocess
from typing import List, Optional, Sequence

from .constants import DEFAULT_TIMEOUT


def run_command(cmd: Sequence[str], timeout: int = DEFAULT_TIMEOUT) -> str:
    """Execute a command and return its output as a string."""
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout)
    return out.decode(errors="ignore")


def build_adb_command(adb: str, device: Optional[str], args: Sequence[str]) -> List[str]:
    """Build ADB command with optional device specification."""
    base = [adb]
    if device:
        base += ["-s", device]
    return base + list(args)


def get_connected_devices(adb: str) -> List[str]:
    """Get list of connected ADB devices."""
    out = run_command([adb, "devices"])
    devices = []
    
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    
    return devices


def get_android_version(adb: str, device: Optional[str]) -> Optional[int]:
    """Get Android version from device."""
    out = run_command(build_adb_command(adb, device, ["shell", "getprop", "ro.build.version.release"]))
    match = re.match(r"(\d+)", out.strip())
    return int(match.group(1)) if match else None


def get_activities_dump(adb: str, device: Optional[str]) -> str:
    """Get activities dump from device."""
    return run_command(build_adb_command(adb, device, ["shell", "dumpsys", "activity", "activities"]))


def get_activity_dump(adb: str, device: Optional[str], component: str) -> str:
    """Get specific activity dump from device."""
    return run_command(build_adb_command(adb, device, ["shell", "dumpsys", "activity", component]))


def get_package_dump(adb: str, device: Optional[str], package: str) -> str:
    """Get package dump from device."""
    return run_command(build_adb_command(adb, device, ["shell", "dumpsys", "activity", package]))
