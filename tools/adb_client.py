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


def get_device_info(adb: str, device: str) -> dict:
    """Get detailed device information.
    
    Args:
        adb: ADB executable path
        device: Device serial number
        
    Returns:
        Dictionary with device information
    """
    info = {
        "serial": device,
        "model": "Unknown",
        "manufacturer": "Unknown", 
        "android_version": "Unknown",
        "api_level": "Unknown"
    }
    
    try:
        # Get device model
        model = run_command(build_adb_command(adb, device, ["shell", "getprop", "ro.product.model"]))
        if model.strip():
            info["model"] = model.strip()
        
        # Get manufacturer
        manufacturer = run_command(build_adb_command(adb, device, ["shell", "getprop", "ro.product.manufacturer"]))
        if manufacturer.strip():
            info["manufacturer"] = manufacturer.strip()
        
        # Get Android version
        android_version = run_command(build_adb_command(adb, device, ["shell", "getprop", "ro.build.version.release"]))
        if android_version.strip():
            info["android_version"] = android_version.strip()
        
        # Get API level
        api_level = run_command(build_adb_command(adb, device, ["shell", "getprop", "ro.build.version.sdk"]))
        if api_level.strip():
            info["api_level"] = api_level.strip()
            
    except Exception:
        # If any property fails, keep defaults
        pass
    
    return info


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


def get_current_activity_fast(adb: str, device: Optional[str], android_version: int) -> str:
    """Fast activity lookup using shell grep (like external plugin).
    
    Args:
        adb: ADB executable path
        device: Device serial number
        android_version: Android version number for choosing grep keyword
        
    Returns:
        Activity component string (e.g., "com.example.app/.MainActivity")
    """
    keyword = "topResumedActivity" if android_version >= 12 else "mResumedActivity"
    
    # Use shell command with grep for fast filtering
    cmd = build_adb_command(adb, device, ["shell", "dumpsys", "activity", "activities"])
    cmd_str = " ".join(cmd) + f" | grep {keyword}"
    
    try:
        # Execute shell command with grep
        result = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT, timeout=30)
        output = result.decode(errors="ignore").strip()
        
        if not output:
            return ""
        
        # Extract component from grep output
        # Format: "    mResumedActivity: ActivityRecord{... com.example.app/.MainActivity ...}"
        # or: "    topResumedActivity=ActivityRecord{... com.example.app/.MainActivity ...}"
        match = re.search(r"([A-Za-z0-9_$.]+)/([A-Za-z0-9_$.]+)", output)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
        
        return ""
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, Exception):
        # Fallback to empty string if grep fails
        return ""
