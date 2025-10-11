#!/usr/bin/env python3
"""
ACF CLI: 查找当前 Android Activity 与其包含的 Fragments，并定位本地源码文件。

支持一键或交互打开文件。
"""

import argparse
import os
import sys
import time
import signal
from datetime import datetime
from typing import List, Optional, Sequence, Tuple, Union

# ANSI 颜色码 - 仅保留使用的颜色
class Colors:
    """ANSI 颜色码，用于突出关键信息"""
    RESET = '\033[0m'
    DIM = '\033[2m'        # 灰色 - 用于弱化路径和时间戳
    YELLOW = '\033[33m'    # 黄色 - 用于警告
    RED = '\033[31m'       # 红色 - 用于错误
    CYAN = '\033[36m'      # 青色 - 用于箭头符号

def supports_color() -> bool:
    """检测终端是否支持颜色输出"""
    return (
        hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
        os.environ.get('TERM') != 'dumb' and
        os.environ.get('NO_COLOR') is None
    )

def colorize(text: str, color: str) -> str:
    """为文本添加颜色，如果终端不支持颜色则返回原文本"""
    if supports_color():
        return f"{color}{text}{Colors.RESET}"
    return text

# 跨平台键盘输入检测
try:
    import select
    import tty
    import termios
    HAS_SELECT = True
except ImportError:
    HAS_SELECT = False

try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

# 常量定义
DEFAULT_ADB = "adb"
CANCEL_COMMANDS = ('q', 'quit', 'exit', 'cancel')
DEFAULT_CHOICE = "0"
WATCH_INTERVAL = 2.0  # 实时监控间隔（秒）

# 类型定义
State = Tuple[str, List[str]]  # (activity_component, fragment_names)

# 导入处理
try:
    import argcomplete  # type: ignore
except ImportError:
    argcomplete = None  # type: ignore

try:
    from .adb_client import get_android_version, get_connected_devices, get_activities_dump, get_current_activity_fast, get_device_info
    from .file_finder import find_source_files, get_activity_name
    from .file_opener import open_file, parse_editor_command
    from .fragment_finder import find_fragments_for_activity, find_fragments_for_activity_optimized
    from .parsers import parse_activity_component
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.adb_client import get_android_version, get_connected_devices, get_activities_dump, get_current_activity_fast, get_device_info
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
    
    # 实时监控参数
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="实时监控模式，自动检测 Activity 和 Fragment 变化（按 q 或 Ctrl+C 退出）"
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
        return _interactive_device_selection(devices)
    
    return devices[0]


def _interactive_device_selection(devices: List[str]) -> str:
    """Interactive device selection with detailed information."""
    print("检测到多个设备，请选择要使用的设备：")
    print()
    
    device_infos = []
    for i, device in enumerate(devices):
        try:
            # 获取设备详细信息
            info = get_device_info("adb", device)
            device_infos.append(info)
            
            # 显示设备信息
            print(f"[{i}] {info['serial']}")
            print(f"    型号: {info['model']}")
            print(f"    厂家: {info['manufacturer']}")
            print(f"    Android: {info['android_version']} (API {info['api_level']})")
            print()
        except Exception:
            # 如果获取信息失败，显示基本信息
            device_infos.append({"serial": device, "model": "Unknown", "manufacturer": "Unknown", "android_version": "Unknown", "api_level": "Unknown"})
            print(f"[{i}] {device}")
            print(f"    型号: Unknown")
            print(f"    厂家: Unknown")
            print(f"    Android: Unknown")
            print()
    
    # 获取用户选择
    while True:
        try:
            choice = input(f"请选择设备 (0-{len(devices)-1}, 回车选择第一个): ").strip()
            
            if not choice:  # 回车选择第一个
                selected_device = devices[0]
                print(f"→ 已选择设备: {selected_device}")
                return selected_device
            
            if choice.lower() in CANCEL_COMMANDS:
                print("已取消")
                sys.exit(0)
            
            choice_idx = int(choice)
            if 0 <= choice_idx < len(devices):
                selected_device = devices[choice_idx]
                print(f"→ 已选择设备: {selected_device}")
                return selected_device
            else:
                print(f"无效选择，请输入 0-{len(devices)-1} 之间的数字")
                
        except ValueError:
            print("无效输入，请输入数字或回车")
        except (EOFError, KeyboardInterrupt):
            # 在 EOF 情况下，默认选择第一个设备
            selected_device = devices[0]
            print(f"\n已选择设备: {selected_device}")
            return selected_device


def _print_error(message: str) -> None:
    """Print error message to stderr."""
    error_label = colorize("错误:", Colors.RED)
    print(f"{error_label} {message}", file=sys.stderr)


def get_current_state(adb: str, device: str) -> State:
    """获取当前设备状态（Activity 和 Fragments）。
    
    Args:
        adb: ADB 可执行文件路径
        device: 设备序列号
        
    Returns:
        状态元组 (activity_component, fragment_names)
    """
    try:
        # 获取当前 Activity
        activity_component = get_current_activity_optimized(adb, device)
        
        # 获取 Fragments
        fragment_names = find_fragments_for_activity_optimized(adb, device, activity_component)
        
        return (activity_component, fragment_names or [])
    except Exception:
        # 如果获取状态失败，返回空状态
        return ("", [])


def compare_states(state1: State, state2: State) -> bool:
    """比较两个状态是否相同。
    
    Args:
        state1: 第一个状态
        state2: 第二个状态
        
    Returns:
        True 如果状态相同，False 如果不同
    """
    if not state1 and not state2:
        return True
    if not state1 or not state2:
        return False
    
    activity1, fragments1 = state1
    activity2, fragments2 = state2
    
    return activity1 == activity2 and fragments1 == fragments2


def check_quit_signal(timeout: float) -> bool:
    """检查是否收到退出信号（q键或Ctrl+C）。
    
    Args:
        timeout: 等待超时时间（秒）
        
    Returns:
        True 如果收到退出信号，False 如果超时
    """
    if HAS_SELECT and sys.stdin.isatty():
        # Unix/macOS: 使用 select 非阻塞检测
        try:
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if ready:
                char = sys.stdin.read(1)
                return char.lower() == 'q'
        except (OSError, ValueError):
            pass
    elif HAS_MSVCRT:
        # Windows: 使用 msvcrt 检测
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if msvcrt.kbhit():
                    char = msvcrt.getch()
                    if isinstance(char, bytes):
                        char = char.decode('utf-8', errors='ignore')
                    if char.lower() == 'q':
                        return True
                time.sleep(0.1)
        except (OSError, ValueError):
            pass
    else:
        # 降级方案：纯等待
        time.sleep(timeout)
    
    return False


def handle_watch_interrupt(signum: int, frame) -> None:
    """处理 Ctrl+C 信号。"""
    print("\n实时监控已停止")
    sys.exit(0)


def watch_mode(adb: str, device: str, search_roots: List[str], verbose: bool) -> None:
    """实时监控模式主循环。
    
    Args:
        adb: ADB 可执行文件路径
        device: 设备序列号
        search_roots: 源码搜索根目录列表
        verbose: 是否显示详细调试信息
    """
    # 设置信号处理器
    signal.signal(signal.SIGINT, handle_watch_interrupt)
    
    print("实时监控模式已启动，按 q 或 Ctrl+C 退出")
    print("每2秒检查一次变化...\n")
    
    previous_state = None
    
    try:
        while True:
            # 获取当前状态
            current_state = get_current_state(adb, device)
            
            # 检查状态是否变化
            if not compare_states(current_state, previous_state):
                # 显示当前状态
                activity_component, fragment_names = current_state
                activity_name = get_activity_name(activity_component)
                
                # 显示更新时间戳（只显示时:分:秒）
                timestamp = datetime.now().strftime('%H:%M:%S')
                arrow = colorize("→", Colors.CYAN)
                timestamp_colored = colorize(timestamp, Colors.DIM)
                print(f"\n{arrow} {timestamp_colored}  {activity_name}")
                
                if verbose:
                    print(f"  设备: {device}")
                    print(f"  搜索根目录: {search_roots}")
                    print(f"  Activity 组件: {activity_component}")
                    print(f"  Activity 名称: {activity_name}")
                    print(f"  Fragment 数量: {len(fragment_names)}")
                    if fragment_names:
                        print(f"  Fragment 列表: {fragment_names}")
                    print()
                
                # 查找源码文件
                activity_files = find_source_files([activity_name], search_roots)
                fragment_files = find_source_files(fragment_names, search_roots) if fragment_names else []
                
                if verbose:
                    print(f"  找到的 Activity 文件: {len(activity_files)}")
                    print(f"  找到的 Fragment 文件: {len(fragment_files)}")
                    print()
                
                # 显示 Fragments（watch 模式使用简洁格式）
                if fragment_names:
                    for name in fragment_names:
                        print(f"  • {name}")
                
                previous_state = current_state
            
            # 检查退出信号
            if check_quit_signal(WATCH_INTERVAL):
                break
                
    except KeyboardInterrupt:
        print("\n实时监控已停止")
    except Exception as e:
        _print_error(f"实时监控出错: {str(e)}")
        if verbose:
            import traceback
            print(f"详细错误信息:\n{traceback.format_exc()}")


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
                   fragments: List[Tuple[str, Optional[str]]], 
                   interactive: bool = False) -> List[Tuple[int, str, Optional[str]]]:
    """Display activity and fragment results, return indexed list."""
    indexed: List[Tuple[int, str, Optional[str]]] = []
    
    # 显示 Activity
    _display_activity(activity_name, activity_path, indexed, interactive)
    
    # 显示 Fragments
    _display_fragments(fragments, indexed, interactive)
    
    return indexed


def _display_activity(activity_name: str, activity_path: Optional[str], 
                     indexed: List[Tuple[int, str, Optional[str]]], interactive: bool = False) -> None:
    """Display activity information."""
    indexed.append((0, activity_name, activity_path))
    
    if interactive and activity_path:
        print(f"[0] Activity: {activity_name}")
        print(f"    {colorize(activity_path, Colors.DIM)}")
    else:
        print(f"Activity: {activity_name}")
        if activity_path:
            print(f"  {colorize(activity_path, Colors.DIM)}")
        else:
            print(f"  {colorize('[未找到]', Colors.YELLOW)}")


def _display_fragments(fragments: List[Tuple[str, Optional[str]]], 
                      indexed: List[Tuple[int, str, Optional[str]]], interactive: bool = False) -> None:
    """Display fragment information."""
    if not fragments:
        print(f"\n{colorize('无 Fragment', Colors.YELLOW)}")
        return
    
    print(f"\nFragments ({len(fragments)})")
    print()  # 空行分隔
    
    for idx, (name, path) in enumerate(fragments, start=1):
        indexed.append((idx, name, path))
        if interactive and path:
            print(f"[{idx}] {name}")
            print(f"    {colorize(path, Colors.DIM)}")
        else:
            print(f"  • {name}")
            if path:
                print(f"    {colorize(path, Colors.DIM)}")


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
        print(colorize("无可打开的文件", Colors.YELLOW), file=sys.stderr)
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
    arrow = colorize("→", Colors.CYAN)
    print(f"{arrow} 正在打开: {class_name}")
    open_file(path or "", editor_cmd)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main CLI entry point."""
    args = None
    try:
        args = _parse_arguments(argv)
        device = validate_device(args.adb, args.device)
        search_roots = _parse_search_roots(args.search_roots)
        
        # 检查是否为实时监控模式
        if args.watch:
            watch_mode(args.adb, device, search_roots, args.verbose)
            return 0
        
        # 显示调试信息
        if args.verbose:
            print(f"设备: {device}")
            print(f"搜索根目录: {search_roots}")
            android_version = get_android_version(args.adb, device)
            print(f"Android 版本: {android_version}")
        
        # 获取当前 Activity 和 Fragments (使用优化方法)
        activity_component = get_current_activity_optimized(args.adb, device)
        activity_name = get_activity_name(activity_component)
        fragment_names = find_fragments_for_activity_optimized(args.adb, device, activity_component)
        
        if args.verbose:
            print(f"Activity 组件: {activity_component}")
            print(f"Activity 名称: {activity_name}")
            print(f"Fragment 数量: {len(fragment_names) if fragment_names else 0}")
            if fragment_names:
                print(f"Fragment 列表: {fragment_names}")
        
        # 查找源码文件
        activity_files = find_source_files([activity_name], search_roots)
        fragment_files = find_source_files(fragment_names, search_roots) if fragment_names else []
        
        if args.verbose:
            print(f"找到的 Activity 文件: {len(activity_files)}")
            print(f"找到的 Fragment 文件: {len(fragment_files)}")
        
        # 显示结果
        activity_path = activity_files[0][1] if activity_files else None
        indexed = display_results(activity_name, activity_path, fragment_files, interactive=args.open)
        
        # 处理文件打开
        handle_file_opening(indexed, args.open_all, args.open, args.editor)
        
        return 0
        
    except Exception as e:
        _print_error(str(e))
        if args and args.verbose:
            import traceback
            print(f"详细错误信息:\n{traceback.format_exc()}")
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