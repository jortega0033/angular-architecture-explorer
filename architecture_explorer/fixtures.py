"""Read-only index of the bundled fixture files."""

from __future__ import annotations

import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

MAX_RESULTS = 200
MAX_QUERY = 200
MAX_EXCERPT = 200


def _split_lines(text: str) -> list[str]:
    if text == "":
        return []
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


class FixtureIndex:
    """Immutable in-memory index: logical path -> list of lines."""

    def __init__(self, root: Path = FIXTURES_DIR) -> None:
        self.root = root
        self._files: dict[str, list[str]] = {}
        root_resolved = root.resolve()
        for dirpath, dirnames, filenames in os.walk(root_resolved, followlinks=False):
            dirnames.sort()
            for name in sorted(filenames):
                if not name.endswith(".ts"):
                    continue
                full = Path(dirpath) / name
                if full.is_symlink() or not full.is_file():
                    continue
                rel = full.relative_to(root_resolved).as_posix()
                text = full.read_bytes().decode("utf-8", errors="replace")
                self._files[rel] = _split_lines(text)
        self._sorted = sorted(self._files)

    def __len__(self) -> int:
        return len(self._files)

    def has(self, path: object) -> bool:
        return isinstance(path, str) and path in self._files

    def line_count(self, path: str) -> int:
        return len(self._files[path])

    def listing(self) -> list[dict]:
        return [{"path": p, "lines": len(self._files[p])} for p in self._sorted]

    def lines(self, path: str) -> list[str] | None:
        """Lines for an indexed logical path, else None (never touches disk)."""
        if not isinstance(path, str) or not path:
            return None
        if "\\" in path or "\x00" in path or path.startswith("/"):
            return None
        if any(seg in ("", ".", "..") for seg in path.split("/")):
            return None
        found = self._files.get(path)
        return list(found) if found is not None else None

    def search(self, q: str) -> tuple[list[dict], bool]:
        """Literal, case-sensitive per-line search. Returns (results, truncated)."""
        if q == "":
            return [], False
        results: list[dict] = []
        for path in self._sorted:
            for number, line in enumerate(self._files[path], start=1):
                if q in line:
                    if len(results) >= MAX_RESULTS:
                        return results, True
                    excerpt = line.rstrip("\r").strip()[:MAX_EXCERPT]
                    results.append({"path": path, "line": number, "excerpt": excerpt})
        return results, False
