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
    
    This is used when parsing the full activity dumpsys output to ensure
    we only get fragments from the current activity, not other activities.
    """
    lines = dumpsys_text.splitlines()
    fragments = []
    
    # Find the section for our specific activity
    activity_found = False
    in_activity_section = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Look for our activity in the dumpsys output
        if component in line or f"{component.split('/')[-1]}" in line:
            activity_found = True
            in_activity_section = True
            continue
        
        # If we're in our activity's section, look for fragment information
        if in_activity_section and activity_found:
            # Check for fragment sections
            if any(line_stripped.startswith(anchor) for anchor in FRAGMENT_ANCHORS):
                # Parse fragments in this section
                j = i + 1
                while j < len(lines):
                    current_line = lines[j].strip()
                    if not current_line:
                        break
                    if any(current_line.startswith(x) for x in (
                        *FRAGMENT_STOPPERS,
                        "Activity #", "Task #", "Stack #"
                    )):
                        break
                    
                    fragment_name = _extract_fragment_name(current_line)
                    if fragment_name and fragment_name not in fragments:
                        fragments.append(fragment_name)
                    j += 1
                
                # If we found fragments, we can stop looking
                if fragments:
                    break
            
            # If we hit another activity or task, we're done with our activity's section
            elif (line_stripped.startswith("Activity #") or 
                  line_stripped.startswith("Task #") or 
                  line_stripped.startswith("Stack #") or
                  (line_stripped and not line_stripped.startswith(" ") and not line_stripped.startswith("\t"))):
                in_activity_section = False
                break
    
    # Filter out system fragments
    return [f for f in fragments if f not in SYSTEM_FRAGMENTS and len(f) > 0]


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
