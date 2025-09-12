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
    keys = ["topResumedActivity", "mResumedActivity"] if prefer_top else ["mResumedActivity", "topResumedActivity"]
    for line in text.splitlines():
        for key in keys:
            if key in line:
                m = re.search(r"([A-Za-z0-9_$.]+)/([A-Za-z0-9_$.]+)", line)
                if m:
                    return f"{m.group(1)}/{m.group(2)}"
    raise RuntimeError("未在 dumpsys 中找到当前 Activity（mResumedActivity/topResumedActivity）。")


def parse_fragments_from_dumpsys(text: str) -> List[str]:
    frags: List[str] = []
    in_added = False
    for raw in text.splitlines():
        s = raw.strip()
        if not in_added and s.startswith("Added Fragments:"):
            in_added = True
            continue
        if in_added:
            if s.startswith(("Removed Fragments:", "AutofillManager:", "Back Stack:", "Loaders:", "FragmentManager state:")):
                break
            m = re.match(r"#\d+[:]?[\s]+([A-Za-z0-9_$.]+)", s)
            if not m:
                m = re.match(r"#?\s*#\d+[:]?[\s]+([A-Za-z0-9_$.]+)", s)
            if m:
                name = m.group(1).split(".")[-1]
                if name not in frags:
                    frags.append(name)
    if not frags:
        for raw in reversed(text.splitlines()):
            s = raw.strip()
            if s.startswith("Added Fragments:"):
                break
            m = re.match(r"#\d+[:]?[\s]+([A-Za-z0-9_$.]+)", s)
            if m:
                name = m.group(1).split(".")[-1]
                if name not in frags:
                    frags.append(name)
            if s.startswith("AutofillManager:"):
                break
    noise = {"ReportFragment", "SupportRequestManagerFragment", "AutofillManager"}
    return [f for f in frags if f not in noise]


def list_fragments_for_component(adb: str, device: Optional[str], component: str) -> List[str]:
    outs: List[str] = []
    try:
        outs.append(run(adb_cmd(adb, device, ["shell", "dumpsys", "activity", component])))
    except Exception:
        pass
    try:
        outs.append(run(adb_cmd(adb, device, ["shell", "dumpsys", "activity", component.split("/", 1)[0]])))
    except Exception:
        pass
    for text in outs:
        fr = parse_fragments_from_dumpsys(text)
        if fr:
            return fr
    return []


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
    targets = {name: None for name in classnames}
    wanted = {f"{name}.kt" for name in classnames} | {f"{name}.java" for name in classnames}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {".git", ".gradle", "build", "out", "node_modules", "venv", "__pycache__"}]
            for fn in filenames:
                if fn in wanted:
                    cls = fn.rsplit(".", 1)[0]
                    if targets.get(cls) is None:
                        targets[cls] = os.path.abspath(os.path.join(dirpath, fn))
        if all(v is not None for v in targets.values()):
            break
    return [(k, targets[k]) for k in classnames]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Find current Android Activity and Fragments, map to local source files, and optionally open them.")
    parser.add_argument("--adb", help="Path to adb (default: use 'adb' in PATH)", default=os.environ.get("ADB", "adb"))
    parser.add_argument("--device", help="ADB device serial (default: auto, requires 0 or 1 device)")
    parser.add_argument("--search-roots", help="Comma-separated source roots to search for classes (default: current directory)")
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
