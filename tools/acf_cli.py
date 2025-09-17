#!/usr/bin/env python3
"""
CLI: 查找当前 Android Activity 与其包含的 Fragments，并定位本地源码文件。
KISS 实现：仅保留必要参数与功能，支持一键或交互打开文件。
"""

import argparse
import os
import re
import shlex
import subprocess
import sys
from typing import Iterable, List, Optional, Sequence, Tuple

try:
    import argcomplete  # type: ignore
except Exception:  # pragma: no cover
    argcomplete = None  # type: ignore


def run(cmd: Sequence[str], timeout: int = 10) -> str:
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout)
    return out.decode(errors="ignore")


def adb_cmd(adb: str, device: Optional[str], args: Sequence[str]) -> List[str]:
    base = [adb]
    if device:
        base += ["-s", device]
    return base + list(args)


def devices(adb: str) -> List[str]:
    out = run([adb, "devices"])  # e.g., "emulator-5554\tdevice"
    res: List[str] = []
    for line in out.splitlines():
        s = line.strip()
        if not s or s.startswith("List of devices"):
            continue
        parts = s.split()
        if len(parts) >= 2 and parts[1] == "device":
            res.append(parts[0])
    return res


def android_version(adb: str, device: Optional[str]) -> Optional[int]:
    out = run(adb_cmd(adb, device, ["shell", "getprop", "ro.build.version.release"]))
    m = re.match(r"(\d+)", out.strip())
    return int(m.group(1)) if m else None


def parse_activity_component_from_dumpsys(text: str, prefer_top: bool) -> str:
    """Extract the ``package/activity`` component from ``dumpsys`` output."""
    keys = ["topResumedActivity", "mResumedActivity"] if prefer_top else ["mResumedActivity", "topResumedActivity"]
    for line in text.splitlines():
        for key in keys:
            if key in line:
                # Match lines like "topResumedActivity: com.foo/.MainActivity"
                m = re.search(r"([A-Za-z0-9_$.]+)/([A-Za-z0-9_$.]+)", line)
                if m:
                    return f"{m.group(1)}/{m.group(2)}"
    raise RuntimeError("未在 dumpsys 中找到当前 Activity（mResumedActivity/topResumedActivity）。")


def parse_fragments_from_dumpsys(text: str, package_hint: Optional[str] = None) -> List[str]:
    """Parse fragment names from ``dumpsys activity`` text.

    Enhanced parsing based on external plugin implementations:
    - Supports both "Added Fragments:" and "Active Fragments:" anchors
    - Handles various Android versions and OEM variants
    - More precise fragment extraction with proper state detection
    - Filters out system/framework fragments
    """
    anchors = ("Added Fragments:", "Active Fragments:")
    stoppers = (
        "Removed Fragments:",
        "AutofillManager:",
        "Back Stack:",
        "Loaders:",
        "FragmentManager state:",
        "Host callbacks:",
        "FragmentManager:",
        "View Hierarchy:",
        "Window #",
    )

    lines = text.splitlines()
    frags: List[str] = []
    
    # First pass: look for fragment sections with package gating
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if any(line.startswith(a) for a in anchors):
            # Package gating: check if package is in vicinity
            if package_hint:
                # Look in the entire text for package name since package info might be at the beginning
                if package_hint not in text:
                    i += 1
                    continue
            
            # Collect fragment lines until a stopper
            j = i + 1
            while j < len(lines):
                current_line = lines[j].strip()
                if not current_line:
                    break
                if any(current_line.startswith(x) for x in stoppers):
                    break
                
                # Extract fragment name using more precise patterns
                fragment_name = extract_fragment_name_from_line(current_line)
                if fragment_name and fragment_name not in frags:
                    frags.append(fragment_name)
                j += 1
            i = j
            continue
        i += 1

    # Second pass: fallback without package gating if no fragments found
    if not frags:
        for idx, line in enumerate(lines):
            if any(line.strip().startswith(a) for a in anchors):
                # Look ahead for fragment lines
                for j in range(idx + 1, min(len(lines), idx + 30)):
                    current_line = lines[j].strip()
                    if not current_line:
                        continue
                    if any(current_line.startswith(x) for x in stoppers):
                        break
                    
                    fragment_name = extract_fragment_name_from_line(current_line)
                    if fragment_name and fragment_name not in frags:
                        frags.append(fragment_name)
                if frags:
                    break

    # Filter out system/framework fragments
    system_fragments = {
        "ReportFragment", "SupportRequestManagerFragment", "AutofillManager",
        "DialogFragment", "ListFragment", "PreferenceFragment", "WebViewFragment",
        "Fragment", "androidx.fragment.app.Fragment", "android.app.Fragment"
    }
    
    return [f for f in frags if f not in system_fragments and len(f) > 0]


def extract_fragment_name_from_line(line: str) -> Optional[str]:
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
    # #0 com.example.app.ui.HomeFragment{123456}
    # #1: com.example.app.ui.child.ChildFragment{abcdef}
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
        if is_valid_fragment_name(class_name):
            return class_name
    
    # Pattern 2: Direct class name with optional braces
    # HomeFragment{123456}
    # com.example.app.ui.TabFragment{000000}
    if "Fragment" in line:
        # Remove braces and content inside
        clean_line = re.sub(r'\{[^}]*\}', '', line)
        
        # Split by spaces and find the fragment name
        parts = clean_line.split()
        for part in parts:
            if "Fragment" in part:
                # Extract class name (last part after dots)
                class_name = part.split(".")[-1]
                if is_valid_fragment_name(class_name):
                    return class_name
    
    return None


def is_valid_fragment_name(name: str) -> bool:
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


def list_fragments_for_component(adb: str, device: Optional[str], component: str) -> List[str]:
    """Get fragments for a specific activity component.
    
    Uses multiple strategies to find fragments:
    1. Direct component dumpsys (most precise)
    2. Package-level dumpsys (fallback)
    3. Full activity dumpsys with strict filtering (last resort)
    """
    outs: List[str] = []
    pkg = component.split("/", 1)[0]
    
    # Strategy 1: Direct component dumpsys - most precise
    try:
        out = run(adb_cmd(adb, device, ["shell", "dumpsys", "activity", component]))
        if out.strip():
            outs.append(out)
    except Exception:
        pass
    
    # Strategy 2: Package-level dumpsys - good fallback
    try:
        out = run(adb_cmd(adb, device, ["shell", "dumpsys", "activity", pkg]))
        if out.strip():
            outs.append(out)
    except Exception:
        pass
    
    # Strategy 3: Full activity dumpsys with strict filtering - last resort
    try:
        out = run(adb_cmd(adb, device, ["shell", "dumpsys", "activity"]))
        if out.strip():
            outs.append(out)
    except Exception:
        pass
    
    # Parse fragments with increasing strictness
    for i, text in enumerate(outs):
        if i < 2:
            # For direct component and package dumpsys, use less strict filtering
            fr = parse_fragments_from_dumpsys(text, package_hint=pkg)
            if fr:
                return fr
        else:
            # For full activity dumpsys, use strict filtering to avoid other activities' fragments
            fr = parse_fragments_from_dumpsys_strict(text, component, pkg)
            if fr:
                return fr
    
    return []


def parse_fragments_from_dumpsys_strict(text: str, component: str, package_hint: str) -> List[str]:
    """Parse fragments with strict filtering to avoid other activities' fragments.
    
    This is used when parsing the full activity dumpsys output to ensure
    we only get fragments from the current activity, not other activities.
    """
    lines = text.splitlines()
    frags: List[str] = []
    
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
            if any(line_stripped.startswith(anchor) for anchor in ("Added Fragments:", "Active Fragments:")):
                # Parse fragments in this section
                j = i + 1
                while j < len(lines):
                    current_line = lines[j].strip()
                    if not current_line:
                        break
                    if any(current_line.startswith(x) for x in (
                        "Removed Fragments:", "AutofillManager:", "Back Stack:", 
                        "Loaders:", "FragmentManager state:", "Host callbacks:",
                        "FragmentManager:", "View Hierarchy:", "Window #",
                        "Activity #", "Task #", "Stack #"
                    )):
                        break
                    
                    fragment_name = extract_fragment_name_from_line(current_line)
                    if fragment_name and fragment_name not in frags:
                        frags.append(fragment_name)
                    j += 1
                
                # If we found fragments, we can stop looking
                if frags:
                    break
            
            # If we hit another activity or task, we're done with our activity's section
            elif (line_stripped.startswith("Activity #") or 
                  line_stripped.startswith("Task #") or 
                  line_stripped.startswith("Stack #") or
                  (line_stripped and not line_stripped.startswith(" ") and not line_stripped.startswith("\t"))):
                in_activity_section = False
                break
    
    # Filter out system/framework fragments
    system_fragments = {
        "ReportFragment", "SupportRequestManagerFragment", "AutofillManager",
        "DialogFragment", "ListFragment", "PreferenceFragment", "WebViewFragment",
        "Fragment", "androidx.fragment.app.Fragment", "android.app.Fragment"
    }
    
    return [f for f in frags if f not in system_fragments and len(f) > 0]


def default_open_cmd() -> Optional[List[str]]:
    if sys.platform == "darwin":
        return ["open"]
    if sys.platform.startswith("linux"):
        return ["xdg-open"]
    if sys.platform.startswith("win"):
        return None  # use os.startfile
    return None


def open_file(path: str, editor_cmd: Optional[List[str]] = None) -> None:
    if sys.platform.startswith("win"):
        try:
            os.startfile(path)  # type: ignore[attr-defined]
            return
        except Exception:
            pass
        subprocess.Popen(["cmd", "/c", "start", "", path], shell=False)
        return
    cmd = editor_cmd or default_open_cmd()
    if not cmd:
        raise RuntimeError("无法确定打开文件的命令，请使用 --editor 指定。")
    subprocess.Popen(cmd + [path])


def find_sources_for_classnames(classnames: Iterable[str], roots: List[str]) -> List[Tuple[str, Optional[str]]]:
    """Search ``roots`` for Kotlin/Java files matching ``classnames``."""
    targets = {name: None for name in classnames}  # map class name -> resolved path
    wanted = {f"{name}.kt" for name in classnames} | {f"{name}.java" for name in classnames}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip common build or VCS directories to reduce noise
            dirnames[:] = [
                d
                for d in dirnames
                if d not in {".git", ".gradle", "build", "out", "node_modules", "venv", "__pycache__"}
            ]
            for fn in filenames:
                if fn in wanted:
                    cls = fn.rsplit(".", 1)[0]
                    if targets.get(cls) is None:
                        targets[cls] = os.path.abspath(os.path.join(dirpath, fn))
        if all(v is not None for v in targets.values()):
            break  # stop searching once all classes are resolved
    return [(k, targets[k]) for k in classnames]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Find current Android Activity and Fragments, map to local source files, and optionally open them."
    )
    parser.add_argument("--adb", help="Path to adb (default: use 'adb' in PATH)", default=os.environ.get("ADB", "adb"))
    parser.add_argument("--device", help="ADB device serial (default: auto, requires 0 or 1 device)")
    parser.add_argument(
        "--search-roots",
        help="Comma-separated source roots to search for classes (default: current directory)",
    )
    parser.add_argument("--open", action="store_true", help="交互选择并打开定位到的文件")
    parser.add_argument("--open-all", action="store_true", help="打开所有已定位到的文件")
    parser.add_argument("--editor", help="自定义打开命令，例如 'code' 或 '/Applications/IntelliJ IDEA.app'", default=None)
    if argcomplete is not None:  # type: ignore
        try:
            argcomplete.autocomplete(parser)  # type: ignore
        except Exception:
            pass
    args = parser.parse_args(argv)

    adb = args.adb
    serial = args.device
    roots = [p for p in (args.search_roots.split(",") if args.search_roots else [os.getcwd()]) if p]

    # Device
    devs = devices(adb)
    if serial is None:
        if len(devs) == 0:
            print("[错误] 未检测到设备，请连接设备并授权 ADB。", file=sys.stderr)
            return 2
        if len(devs) > 1:
            print("[错误] 检测到多个设备，请使用 --device 指定序列号：", file=sys.stderr)
            for d in devs:
                print(f"  - {d}", file=sys.stderr)
            return 2
        serial = devs[0]

    # Activity
    ver = android_version(adb, serial)
    activities_dump = run(adb_cmd(adb, serial, ["shell", "dumpsys", "activity", "activities"]))
    comp = parse_activity_component_from_dumpsys(activities_dump, prefer_top=((ver or 0) >= 12))
    activity_simple = comp.split("/")[-1].split(".")[-1]

    # Fragments
    frags = list_fragments_for_component(adb, serial, comp)

    # Map to files
    act_map = find_sources_for_classnames([activity_simple], roots)
    frag_map = find_sources_for_classnames(frags, roots) if frags else []

    # Output（分组，索引 0 为 Activity）
    indexed: List[Tuple[int, str, Optional[str]]] = []
    print("当前 Activity:")
    act_name, act_path = act_map[0][0], act_map[0][1]
    indexed.append((0, act_name, act_path))
    print(f"  [0] {act_name}: {act_path if act_path else '[未找到]，请调整 --search-roots 或确认源码存在'}")

    print("\n当前 Fragments:")
    if not frag_map:
        print("  [无 Fragment]")
    else:
        for idx, (cname, path) in enumerate(frag_map, start=1):
            indexed.append((idx, cname, path))
            print(f"  [{idx}] {cname}: {path if path else '[未找到]，请调整 --search-roots 或确认源码存在'}")

    # Open
    if args.open_all:
        editor_cmd = shlex.split(args.editor) if args.editor else default_open_cmd()
        for _, _, path in indexed:
            if path:
                open_file(path, editor_cmd)
        return 0

    if args.open:
        available = [(i, c, p) for (i, c, p) in indexed if p]
        if not available:
            print("[信息] 无可打开的文件。", file=sys.stderr)
            return 0
        try:
            choice = input("输入序号打开文件（0 为 Activity，回车取消）：").strip()
        except EOFError:
            choice = ""
        if choice:
            try:
                pick = int(choice)
            except ValueError:
                print("[错误] 无效的序号。", file=sys.stderr)
                return 2
            match = next(((i, c, p) for (i, c, p) in available if i == pick), None)
            if not match:
                print("[错误] 未找到对应序号。", file=sys.stderr)
                return 2
            _, _, pth = match
            editor_cmd = shlex.split(args.editor) if args.editor else default_open_cmd()
            open_file(pth or "", editor_cmd)

    return 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
