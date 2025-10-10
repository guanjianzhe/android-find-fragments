"""Parsers for Android dumpsys output."""

import re
from typing import List, Optional

from .constants import ACTIVITY_KEYS, FRAGMENT_ANCHORS, FRAGMENT_STOPPERS, SYSTEM_FRAGMENTS


def parse_activity_component(dumpsys_text: str, prefer_top: bool = True) -> str:
    """Parse current activity component from dumpsys activities output."""
    keys = ACTIVITY_KEYS if prefer_top else list(reversed(ACTIVITY_KEYS))
    
    for line in dumpsys_text.splitlines():
        for key in keys:
            if key in line:
                # Match lines like "topResumedActivity: com.foo/.MainActivity"
                match = re.search(r"([A-Za-z0-9_$.]+)/([A-Za-z0-9_$.]+)", line)
                if match:
                    return f"{match.group(1)}/{match.group(2)}"
    
    raise RuntimeError("未在 dumpsys 中找到当前 Activity（mResumedActivity/topResumedActivity）。")


def parse_fragments(dumpsys_text: str, package_hint: Optional[str] = None) -> List[str]:
    """Parse fragment names from dumpsys activity output.
    
    Args:
        dumpsys_text: Raw dumpsys output
        package_hint: Optional package name to filter fragments
        
    Returns:
        List of fragment class names
    """
    lines = dumpsys_text.splitlines()
    fragments = []
    
    # First pass: look for fragment sections with package gating
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if any(line.startswith(anchor) for anchor in FRAGMENT_ANCHORS):
            # Package gating: check if package is in the entire text
            if package_hint and package_hint not in dumpsys_text:
                i += 1
                continue
            
            # Collect fragment lines until a stopper
            j = i + 1
            while j < len(lines):
                current_line = lines[j].strip()
                if not current_line:
                    break
                if any(current_line.startswith(stop) for stop in FRAGMENT_STOPPERS):
                    break
                
                fragment_name = _extract_fragment_name(current_line)
                if fragment_name and fragment_name not in fragments:
                    fragments.append(fragment_name)
                j += 1
            i = j
            continue
        i += 1

    # Second pass: fallback without package gating if no fragments found
    if not fragments:
        for idx, line in enumerate(lines):
            if any(line.strip().startswith(anchor) for anchor in FRAGMENT_ANCHORS):
                # Look ahead for fragment lines
                for j in range(idx + 1, min(len(lines), idx + 30)):
                    current_line = lines[j].strip()
                    if not current_line:
                        continue
                    if any(current_line.startswith(stop) for stop in FRAGMENT_STOPPERS):
                        break
                    
                    fragment_name = _extract_fragment_name(current_line)
                    if fragment_name and fragment_name not in fragments:
                        fragments.append(fragment_name)
                if fragments:
                    break

    # Filter out system fragments
    return [f for f in fragments if f not in SYSTEM_FRAGMENTS and len(f) > 0]


def parse_fragments_strict(dumpsys_text: str, component: str, package_hint: str) -> List[str]:
    """Parse fragments with strict filtering to avoid other activities' fragments.
    
    This implementation is based on the external plugin's approach:
    1. Parse lines in reverse order to find the most recent activity
    2. Use a flag-based approach to ensure we only parse fragments from the current activity
    3. Filter out system fragments and invalid names
    """
    lines = dumpsys_text.splitlines()
    fragments = []
    flag = 0
    
    # Parse lines in reverse order (like the external plugin)
    for line in reversed(lines):
        line_stripped = line.strip()
        
        # If we're in fragment parsing mode (flag >= 1)
        if flag >= 1:
            # Check for lines starting with # followed by digits (fragment entries)
            if (line_stripped.startswith("#") and 
                line_stripped[1:].strip() and
                line_stripped[1:].strip()[0].isdigit()):
                
                # Extract fragment name from line like "#0: com.example.Fragment{123456}"
                fragment_name = _extract_fragment_name_from_line(line_stripped)
                if fragment_name and fragment_name not in fragments:
                    fragments.append(fragment_name)
                    flag = 1  # Found at least one fragment
            
            # Stop parsing if we hit a stopper (and we've found at least one fragment marker)
            elif any(line_stripped.startswith(stop) for stop in FRAGMENT_STOPPERS):
                if flag == 1:  # We found fragments, stop here
                    break
        
        # Check for fragment section markers
        if line_stripped.startswith("Added Fragments:"):
            if flag == 0:
                flag = 2  # Mark that we found "Added Fragments:" but no fragments yet
            elif flag == 1:
                # We already found fragments, this is from another activity, stop
                break
    
    # Filter out system fragments and reverse (since we parsed in reverse order)
    filtered = [f for f in fragments if f not in SYSTEM_FRAGMENTS and len(f) > 0]
    return list(reversed(filtered))


def _extract_fragment_name_from_line(line: str) -> Optional[str]:
    """Extract fragment class name from a dumpsys line.
    
    Handles formats like:
    - "#0 com.example.app.ui.HomeFragment{123456}"
    - "#0: com.example.app.ui.HomeFragment{123456}"
    """
    line = line.strip()
    if not line or not line.startswith("#"):
        return None
    
    # Remove the # and digits
    content = line[1:].strip()
    
    # Skip digits at the start
    while content and content[0].isdigit():
        content = content[1:]
    content = content.strip()
    
    # Remove optional colon
    if content.startswith(":"):
        content = content[1:].strip()
    
    # Extract the class name (before { or space)
    class_name = content.split("{")[0].split()[0] if content else ""
    
    # Extract just the class name (last part after dots)
    if "." in class_name:
        class_name = class_name.split(".")[-1]
    
    # Check if it's a valid fragment name
    if _is_valid_fragment_name(class_name):
        return class_name
    
    return None


def _extract_fragment_name(line: str) -> Optional[str]:
    """Extract fragment class name from a dumpsys line.
    
    Handles various formats:
    - #0 com.example.app.ui.HomeFragment{123456}
    - #1: com.example.app.ui.child.ChildFragment{abcdef}
    - HomeFragment{123456}
    - com.example.app.ui.TabFragment{000000}
    """
    line = line.strip()
    if not line:
        return None
    
    # Pattern 1: Lines starting with # followed by index
    if line.startswith("#"):
        # Remove the #index part
        content = line[1:].strip()
        if content.startswith(":"):
            content = content[1:].strip()
        
        # Find the first space to get the class name
        space_idx = content.find(" ")
        if space_idx > 0:
            class_name = content[:space_idx]
        else:
            class_name = content
        
        # Extract just the class name (last part after dots)
        if "." in class_name:
            class_name = class_name.split(".")[-1]
        
        # Check if it's a valid fragment name
        if _is_valid_fragment_name(class_name):
            return class_name
    
    # Pattern 2: Direct class name with optional braces
    if "Fragment" in line:
        # Remove braces and content inside
        clean_line = re.sub(r'\{[^}]*\}', '', line)
        
        # Split by spaces and find the fragment name
        parts = clean_line.split()
        for part in parts:
            if "Fragment" in part:
                # Extract class name (last part after dots)
                class_name = part.split(".")[-1]
                if _is_valid_fragment_name(class_name):
                    return class_name
    
    return None


def _is_valid_fragment_name(name: str) -> bool:
    """Check if a name is a valid fragment class name."""
    if not name or len(name) < 3:
        return False
    
    # Must end with Fragment
    if not name.endswith("Fragment"):
        return False
    
    # Must start with uppercase letter
    if not name[0].isupper():
        return False
    
    # Should not contain special characters except underscores
    if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', name):
        return False
    
    # Filter out obvious system fragments
    system_patterns = [
        r'^.*Fragment$',  # Generic Fragment
        r'^.*DialogFragment$',  # DialogFragment
        r'^.*ListFragment$',  # ListFragment
        r'^.*PreferenceFragment$',  # PreferenceFragment
        r'^.*WebViewFragment$',  # WebViewFragment
    ]
    
    for pattern in system_patterns:
        if re.match(pattern, name) and name in {
            "Fragment", "DialogFragment", "ListFragment", 
            "PreferenceFragment", "WebViewFragment"
        }:
            return False
    
    return True
