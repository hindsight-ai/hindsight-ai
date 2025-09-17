#!/usr/bin/env python3
"""
Generate architecture documentation for the repository.

Creates docs/architecture.md with:
- Project layout (folders, subfolders, and all .py files)
- List of Python modules with their docstrings (first line summary)

Excludes common virtualenv, cache, and vendor directories.
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path
from typing import Iterable, Tuple, List

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
OUTPUT_FILE = DOCS_DIR / "architecture.md"

EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    ".uv-cache",
    "node_modules",
    "__pycache__",
    "coverage_html",
}

def should_exclude(path: Path) -> bool:
    parts = set(path.parts)
    return any(part in EXCLUDE_DIRS for part in parts)

def iter_python_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded dirs in-place for efficiency
        dirnames[:] = [d for d in dirnames if not should_exclude(Path(dirpath) / d)]
        if should_exclude(Path(dirpath)):
            continue
        for f in filenames:
            if f.endswith(".py"):
                yield Path(dirpath) / f

def build_tree_listing(root: Path) -> str:
    """Return a tree-like listing of directories and .py files from root."""
    lines: List[str] = []
    base_len = len(str(root)) + 1
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded
        dirnames[:] = [d for d in sorted(dirnames) if not should_exclude(Path(dirpath) / d)]
        if should_exclude(Path(dirpath)):
            continue
        rel_dir = str(Path(dirpath))[base_len:] or "."
        lines.append(rel_dir)
        for f in sorted(filenames):
            if f.endswith(".py"):
                lines.append(f"  - {f}")
    return "\n".join(lines)

def get_module_docstring(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
        mod = ast.parse(text)
        doc = ast.get_docstring(mod) or ""
        if not doc:
            return "(no module docstring)"
        # First non-empty line as summary
        for line in doc.strip().splitlines():
            if line.strip():
                return line.strip()
        return "(empty docstring)"
    except Exception as e:
        return f"(error reading: {e})"

def main() -> int:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    tree_md = build_tree_listing(REPO_ROOT)
    modules = sorted(iter_python_files(REPO_ROOT))

    # Build module list with docstrings
    module_lines: List[str] = []
    for p in modules:
        if should_exclude(p):
            continue
        rel = p.relative_to(REPO_ROOT)
        doc = get_module_docstring(p)
        module_lines.append(f"- `{rel}`: {doc}")

    content = f"""# Architecture Overview

## Project Layout

```
{tree_md}
```

## Python Modules and Docstrings

{os.linesep.join(module_lines)}
"""

    OUTPUT_FILE.write_text(content, encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
