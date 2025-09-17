"""File finder for locating source files."""

import os
from typing import Iterable, List, Optional, Tuple

from .constants import SKIP_DIRECTORIES


def find_source_files(classnames: Iterable[str], search_roots: List[str]) -> List[Tuple[str, Optional[str]]]:
    """Search for Kotlin/Java files matching class names in the given roots.
    
    Args:
        classnames: List of class names to search for
        search_roots: List of directories to search in
        
    Returns:
        List of tuples (class_name, file_path)
    """
    targets = {name: None for name in classnames}
    wanted_files = {f"{name}.kt" for name in classnames} | {f"{name}.java" for name in classnames}
    
    for root in search_roots:
        if not os.path.isdir(root):
            continue
            
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip common build or VCS directories to reduce noise
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRECTORIES]
            
            for filename in filenames:
                if filename in wanted_files:
                    class_name = filename.rsplit(".", 1)[0]
                    if targets.get(class_name) is None:
                        targets[class_name] = os.path.abspath(os.path.join(dirpath, filename))
            
            # Stop searching once all classes are resolved
            if all(v is not None for v in targets.values()):
                break
    
    return [(k, targets[k]) for k in classnames]


def get_activity_name(component: str) -> str:
    """Extract simple activity name from component string."""
    return component.split("/")[-1].split(".")[-1]
