"""Fragment finder for locating fragments in Android activities."""

from typing import List, Optional

from .adb_client import get_activity_dump, get_android_version, get_package_dump
from .parsers import parse_fragments, parse_fragments_strict


def find_fragments_for_activity(adb: str, device: Optional[str], component: str) -> List[str]:
    """Find fragments for a specific activity component.
    
    Uses the most precise method: direct activity dumpsys with strict parsing.
    This ensures we only get fragments from the current activity, not other activities.
    
    Args:
        adb: Path to adb executable
        device: Optional device serial number
        component: Activity component (package/activity)
        
    Returns:
        List of fragment class names
    """
    package = component.split("/", 1)[0]
    
    # Use direct activity dumpsys - most precise method
    try:
        dump = get_activity_dump(adb, device, component)
        if dump.strip():
            fragments = parse_fragments_strict(dump, component, package)
            if fragments:
                return fragments
    except Exception:
        pass
    
    # Fallback: try package-level dumpsys
    try:
        dump = get_package_dump(adb, device, package)
        if dump.strip():
            fragments = parse_fragments_strict(dump, component, package)
            if fragments:
                return fragments
    except Exception:
        pass
    
    return []
