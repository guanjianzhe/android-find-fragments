#!/usr/bin/env python3
"""
ACF CLI: 查找当前 Android Activity 与其包含的 Fragments，并定位本地源码文件。

支持一键或交互打开文件。
"""

import argparse
import os
import sys
from typing import List, Optional, Sequence, Tuple

# 常量定义
DEFAULT_ADB = "adb"
CANCEL_COMMANDS = ('q', 'quit', 'exit', 'cancel')
DEFAULT_CHOICE = "0"

# 导入处理
try:
    import argcomplete  # type: ignore
except ImportError:
    argcomplete = None  # type: ignore

try:
    from .adb_client import get_android_version, get_connected_devices, get_activities_dump, get_current_activity_fast
    from .file_finder import find_source_files, get_activity_name
    from .file_opener import open_file, parse_editor_command
    from .fragment_finder import find_fragments_for_activity, find_fragments_for_activity_optimized
    from .parsers import parse_activity_component
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.adb_client import get_android_version, get_connected_devices, get_activities_dump, get_current_activity_fast
    from tools.file_finder import find_source_files, get_activity_name
    from tools.file_opener import open_file, parse_editor_command
    from tools.fragment_finder import find_fragments_for_activity, find_fragments_for_activity_optimized
    from tools.parsers import parse_activity_component


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Find current Android Activity and Fragments, map to local source files, and optionally open them."
    )
    
    # ADB 相关参数
    parser.add_argument(
        "--adb", 
        help="Path to adb (default: use 'adb' in PATH)", 
        default=os.environ.get("ADB", DEFAULT_ADB)
    )
    parser.add_argument(
        "--device", 
        help="ADB device serial (default: auto, requires 0 or 1 device)"
    )
    
    # 搜索相关参数
    parser.add_argument(
        "--search-roots",
        help="Comma-separated source roots to search for classes (default: current directory)",
    )
    
    # 文件操作参数
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
        help="自定义打开命令，例如 'code'、'/Applications/Android Studio.app' 或 '/Applications/IntelliJ IDEA.app'", 
        default=None
    )
    
    # 调试参数
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细的调试信息"
    )
    
    # 启用自动补全
    _enable_autocomplete(parser)
    
    return parser


def _enable_autocomplete(parser: argparse.ArgumentParser) -> None:
    """Enable argcomplete if available."""
    if argcomplete:
        try:
            argcomplete.autocomplete(parser)
        except Exception:
            pass


def validate_device(adb: str, device: Optional[str]) -> str:
    """Validate device connection and return device serial."""
    devices = get_connected_devices(adb)
    
    if device is None:
        return _handle_auto_device_selection(devices)
    
    if device not in devices:
        _print_error(f"设备 {device} 未连接或未授权。")
        sys.exit(2)
    
    return device


def _handle_auto_device_selection(devices: List[str]) -> str:
    """Handle automatic device selection."""
    if not devices:
        _print_error("未检测到设备，请连接设备并授权 ADB。")
        sys.exit(2)
    
    if len(devices) > 1:
        _print_error("检测到多个设备，请使用 --device 指定序列号：")
        for device in devices:
            print(f"  - {device}", file=sys.stderr)
        sys.exit(2)
    
    return devices[0]


def _print_error(message: str) -> None:
    """Print error message to stderr."""
    print(f"[错误] {message}", file=sys.stderr)


def get_current_activity(adb: str, device: str) -> str:
    """Get current activity component from device."""
    version = get_android_version(adb, device)
    activities_dump = get_activities_dump(adb, device)
    return parse_activity_component(activities_dump, prefer_top=((version or 0) >= 12))


def get_current_activity_optimized(adb: str, device: str) -> str:
    """Get current activity component using optimized approach (shell grep)."""
    version = get_android_version(adb, device)
    if version:
        # Try optimized approach first
        component = get_current_activity_fast(adb, device, version)
        if component:
            return component
    
    # Fallback to original method
    return get_current_activity(adb, device)


def display_results(activity_name: str, activity_path: Optional[str], 
                   fragments: List[Tuple[str, Optional[str]]]) -> List[Tuple[int, str, Optional[str]]]:
    """Display activity and fragment results, return indexed list."""
    indexed: List[Tuple[int, str, Optional[str]]] = []
    
    # 显示 Activity
    _display_activity(activity_name, activity_path, indexed)
    
    # 显示 Fragments
    _display_fragments(fragments, indexed)
    
    return indexed


def _display_activity(activity_name: str, activity_path: Optional[str], 
                     indexed: List[Tuple[int, str, Optional[str]]]) -> None:
    """Display activity information."""
    print("当前 Activity:")
    indexed.append((0, activity_name, activity_path))
    path = activity_path or '[未找到]，请调整 --search-roots 或确认源码存在'
    print(f"  [0] {activity_name}: {path}")


def _display_fragments(fragments: List[Tuple[str, Optional[str]]], 
                      indexed: List[Tuple[int, str, Optional[str]]]) -> None:
    """Display fragment information."""
    print("\n当前 Fragments:")
    if not fragments:
        print("  [无 Fragment]")
        return
    
    for idx, (name, path) in enumerate(fragments, start=1):
        indexed.append((idx, name, path))
        path_display = path or '[未找到]，请调整 --search-roots 或确认源码存在'
        print(f"  [{idx}] {name}: {path_display}")


def handle_file_opening(indexed: List[Tuple[int, str, Optional[str]]], 
                       open_all: bool, open_interactive: bool, 
                       editor_command: Optional[str]) -> None:
    """Handle file opening based on user preferences."""
    if open_all:
        _open_all_files(indexed, editor_command)
    elif open_interactive:
        _open_interactive(indexed, editor_command)


def _open_all_files(indexed: List[Tuple[int, str, Optional[str]]], 
                   editor_command: Optional[str]) -> None:
    """Open all available files."""
    editor_cmd = parse_editor_command(editor_command)
    for _, _, path in indexed:
        if path:
            open_file(path, editor_cmd)


def _open_interactive(indexed: List[Tuple[int, str, Optional[str]]], 
                     editor_command: Optional[str]) -> None:
    """Handle interactive file selection."""
    available = [(i, c, p) for (i, c, p) in indexed if p]
    if not available:
        print("[信息] 无可打开的文件。", file=sys.stderr)
        return
    
    choice = _get_user_choice()
    if not choice:
        return
    
    try:
        pick = int(choice)
    except ValueError:
        print("无效输入")
        return
    
    match = next(((i, c, p) for (i, c, p) in available if i == pick), None)
    if not match:
        print(f"未找到序号 {pick}")
        return
    
    _open_selected_file(match, editor_command)


def _get_user_choice() -> Optional[str]:
    """Get user input choice."""
    print("\n请选择 (回车=0): ", end="", flush=True)
    
    try:
        choice = input().strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        return None
    
    if choice.lower() in CANCEL_COMMANDS:
        print("已取消")
        return None
    
    return choice or DEFAULT_CHOICE


def _open_selected_file(match: Tuple[int, str, Optional[str]], 
                       editor_command: Optional[str]) -> None:
    """Open the selected file."""
    _, class_name, path = match
    editor_cmd = parse_editor_command(editor_command)
    print(f"正在打开: {class_name}")
    open_file(path or "", editor_cmd)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main CLI entry point."""
    args = None
    try:
        args = _parse_arguments(argv)
        device = validate_device(args.adb, args.device)
        search_roots = _parse_search_roots(args.search_roots)
        
        # 显示调试信息
        if args.verbose:
            print(f"[调试] 使用设备: {device}")
            print(f"[调试] 搜索根目录: {search_roots}")
            android_version = get_android_version(args.adb, device)
            print(f"[调试] Android 版本: {android_version}")
        
        # 获取当前 Activity 和 Fragments (使用优化方法)
        activity_component = get_current_activity_optimized(args.adb, device)
        activity_name = get_activity_name(activity_component)
        fragment_names = find_fragments_for_activity_optimized(args.adb, device, activity_component)
        
        if args.verbose:
            print(f"[调试] Activity 组件: {activity_component}")
            print(f"[调试] Activity 名称: {activity_name}")
            print(f"[调试] Fragment 数量: {len(fragment_names) if fragment_names else 0}")
            if fragment_names:
                print(f"[调试] Fragment 列表: {fragment_names}")
        
        # 查找源码文件
        activity_files = find_source_files([activity_name], search_roots)
        fragment_files = find_source_files(fragment_names, search_roots) if fragment_names else []
        
        if args.verbose:
            print(f"[调试] 找到的 Activity 文件: {len(activity_files)}")
            print(f"[调试] 找到的 Fragment 文件: {len(fragment_files)}")
        
        # 显示结果
        activity_path = activity_files[0][1] if activity_files else None
        indexed = display_results(activity_name, activity_path, fragment_files)
        
        # 处理文件打开
        handle_file_opening(indexed, args.open_all, args.open, args.editor)
        
        return 0
        
    except Exception as e:
        _print_error(str(e))
        if args and args.verbose:
            import traceback
            print(f"[调试] 详细错误信息:\n{traceback.format_exc()}")
        return 1


def _parse_arguments(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = setup_argument_parser()
    return parser.parse_args(argv)


def _parse_search_roots(search_roots: Optional[str]) -> List[str]:
    """Parse search roots from comma-separated string."""
    if not search_roots:
        return [os.getcwd()]
    return [p.strip() for p in search_roots.split(",") if p.strip()]


def cli() -> None:
    """CLI entry point for package installation."""
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())