"""Fragment finder for locating fragments in Android activities."""

from typing import List, Optional

from .adb_client import get_activity_dump, get_android_version, get_package_dump
from .parsers import parse_fragments, parse_fragments_strict


def find_fragments_for_activity(adb: str, device: Optional[str], component: str) -> List[str]:
    """Find fragments for a specific activity component.
    
    Uses multiple strategies to find fragments:
    1. Direct component dumpsys (most precise)
    2. Package-level dumpsys (fallback)
    3. Full activity dumpsys with strict filtering (last resort)
    
    Args:
        adb: Path to adb executable
        device: Optional device serial number
        component: Activity component (package/activity)
        
    Returns:
        List of fragment class names
    """
    package = component.split("/", 1)[0]
    
    # Strategy 1: Direct component dumpsys - most precise
    try:
        dump = get_activity_dump(adb, device, component)
        if dump.strip():
            fragments = parse_fragments(dump, package_hint=package)
            if fragments:
                return fragments
    except Exception:
        pass
    
    # Strategy 2: Package-level dumpsys - good fallback
    try:
        dump = get_package_dump(adb, device, package)
        if dump.strip():
            fragments = parse_fragments(dump, package_hint=package)
            if fragments:
                return fragments
    except Exception:
        pass
    
    # Strategy 3: Full activity dumpsys with strict filtering - last resort
    try:
        from .adb_client import get_activities_dump
        dump = get_activities_dump(adb, device)
        if dump.strip():
            fragments = parse_fragments_strict(dump, component, package)
            if fragments:
                return fragments
    except Exception:
        pass
    
    return []
