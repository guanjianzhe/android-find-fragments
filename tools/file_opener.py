"""File opener for opening source files in editors."""

import os
import shlex
import subprocess
import sys
from typing import List, Optional


def get_default_open_command() -> Optional[List[str]]:
    """Get default file opening command for the current platform."""
    if sys.platform == "darwin":
        return ["open"]
    if sys.platform.startswith("linux"):
        return ["xdg-open"]
    if sys.platform.startswith("win"):
        return None  # use os.startfile
    return None


def open_file(file_path: str, editor_command: Optional[List[str]] = None) -> None:
    """Open a file with the specified editor command.
    
    Args:
        file_path: Path to the file to open (supports ~ for home directory)
        editor_command: Optional custom editor command
    """
    # Expand ~ to absolute path for file operations
    expanded_path = os.path.expanduser(file_path)
    if sys.platform.startswith("win"):
        try:
            os.startfile(expanded_path)  # type: ignore[attr-defined]
            return
        except Exception:
            pass
        subprocess.Popen(["cmd", "/c", "start", "", expanded_path], shell=False)
        return
    
    cmd = editor_command or get_default_open_command()
    if not cmd:
        raise RuntimeError("无法确定打开文件的命令，请使用 --editor 指定。")
    
    subprocess.Popen(cmd + [expanded_path])


def parse_editor_command(editor_string: Optional[str]) -> Optional[List[str]]:
    """Parse editor command string into a list."""
    if not editor_string:
        return None
    return shlex.split(editor_string)
