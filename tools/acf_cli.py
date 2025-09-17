#!/usr/bin/env python3
"""
ACF CLI: 查找当前 Android Activity 与其包含的 Fragments，并定位本地源码文件。

简洁实现：模块化设计，支持一键或交互打开文件。
"""

import argparse
import os
import sys
from typing import List, Optional, Sequence, Tuple

try:
    import argcomplete  # type: ignore
except Exception:  # pragma: no cover
    argcomplete = None  # type: ignore

try:
    from .adb_client import get_android_version, get_connected_devices, get_activities_dump
    from .file_finder import find_source_files, get_activity_name
    from .file_opener import open_file, parse_editor_command
    from .fragment_finder import find_fragments_for_activity
    from .parsers import parse_activity_component
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.adb_client import get_android_version, get_connected_devices, get_activities_dump
    from tools.file_finder import find_source_files, get_activity_name
    from tools.file_opener import open_file, parse_editor_command
    from tools.fragment_finder import find_fragments_for_activity
    from tools.parsers import parse_activity_component


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Find current Android Activity and Fragments, map to local source files, and optionally open them."
    )
    parser.add_argument(
        "--adb", 
        help="Path to adb (default: use 'adb' in PATH)", 
        default=os.environ.get("ADB", "adb")
    )
    parser.add_argument(
        "--device", 
        help="ADB device serial (default: auto, requires 0 or 1 device)"
    )
    parser.add_argument(
        "--search-roots",
        help="Comma-separated source roots to search for classes (default: current directory)",
    )
    parser.add_argument(
        "--open", 
        action="store_true", 
        help="交互选择并打开定位到的文件"
    )
    parser.add_argument(
        "--open-all", 
        action="store_true", 
        help="打开所有已定位到的文件"
    )
    parser.add_argument(
        "--editor", 
        help="自定义打开命令，例如 'code' 或 '/Applications/IntelliJ IDEA.app'", 
        default=None
    )
    
    # Enable argcomplete if available
    if argcomplete is not None:  # type: ignore
        try:
            argcomplete.autocomplete(parser)  # type: ignore
        except Exception:
            pass
    
    return parser


def validate_device(adb: str, device: Optional[str]) -> str:
    """Validate device connection and return device serial."""
    devices = get_connected_devices(adb)
    
    if device is None:
        if len(devices) == 0:
            print("[错误] 未检测到设备，请连接设备并授权 ADB。", file=sys.stderr)
            sys.exit(2)
        if len(devices) > 1:
            print("[错误] 检测到多个设备，请使用 --device 指定序列号：", file=sys.stderr)
            for d in devices:
                print(f"  - {d}", file=sys.stderr)
            sys.exit(2)
        return devices[0]
    
    if device not in devices:
        print(f"[错误] 设备 {device} 未连接或未授权。", file=sys.stderr)
        sys.exit(2)
    
    return device


def get_current_activity(adb: str, device: str) -> str:
    """Get current activity component from device."""
    version = get_android_version(adb, device)
    activities_dump = get_activities_dump(adb, device)
    return parse_activity_component(activities_dump, prefer_top=((version or 0) >= 12))


def display_results(activity_name: str, activity_path: Optional[str], 
                   fragments: List[Tuple[str, Optional[str]]]) -> List[Tuple[int, str, Optional[str]]]:
    """Display activity and fragment results, return indexed list."""
    indexed: List[Tuple[int, str, Optional[str]]] = []
    
    print("当前 Activity:")
    indexed.append((0, activity_name, activity_path))
    print(f"  [0] {activity_name}: {activity_path if activity_path else '[未找到]，请调整 --search-roots 或确认源码存在'}")
    
    print("\n当前 Fragments:")
    if not fragments:
        print("  [无 Fragment]")
    else:
        for idx, (fragment_name, fragment_path) in enumerate(fragments, start=1):
            indexed.append((idx, fragment_name, fragment_path))
            print(f"  [{idx}] {fragment_name}: {fragment_path if fragment_path else '[未找到]，请调整 --search-roots 或确认源码存在'}")
    
    return indexed


def handle_file_opening(indexed: List[Tuple[int, str, Optional[str]]], 
                       open_all: bool, open_interactive: bool, 
                       editor_command: Optional[str]) -> None:
    """Handle file opening based on user preferences."""
    if open_all:
        editor_cmd = parse_editor_command(editor_command)
        for _, _, path in indexed:
            if path:
                open_file(path, editor_cmd)
        return
    
    if open_interactive:
        available = [(i, c, p) for (i, c, p) in indexed if p]
        if not available:
            print("[信息] 无可打开的文件。", file=sys.stderr)
            return
        
        try:
            choice = input("输入序号打开文件（0 为 Activity，回车取消）：").strip()
        except EOFError:
            choice = ""
        
        if choice:
            try:
                pick = int(choice)
            except ValueError:
                print("[错误] 无效的序号。", file=sys.stderr)
                sys.exit(2)
            
            match = next(((i, c, p) for (i, c, p) in available if i == pick), None)
            if not match:
                print("[错误] 未找到对应序号。", file=sys.stderr)
                sys.exit(2)
            
            _, _, path = match
            editor_cmd = parse_editor_command(editor_command)
            open_file(path or "", editor_cmd)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main CLI entry point."""
    parser = setup_argument_parser()
    args = parser.parse_args(argv)
    
    # Parse arguments
    adb = args.adb
    device = validate_device(adb, args.device)
    search_roots = [p for p in (args.search_roots.split(",") if args.search_roots else [os.getcwd()]) if p]
    
    try:
        # Get current activity
        activity_component = get_current_activity(adb, device)
        activity_name = get_activity_name(activity_component)
        
        # Find fragments
        fragment_names = find_fragments_for_activity(adb, device, activity_component)
        
        # Map to source files
        activity_files = find_source_files([activity_name], search_roots)
        fragment_files = find_source_files(fragment_names, search_roots) if fragment_names else []
        
        # Display results
        activity_path = activity_files[0][1] if activity_files else None
        indexed = display_results(activity_name, activity_path, fragment_files)
        
        # Handle file opening
        handle_file_opening(indexed, args.open_all, args.open, args.editor)
        
        return 0
        
    except Exception as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1


def cli() -> None:
    """CLI entry point for package installation."""
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())