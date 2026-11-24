"""Workspace with checkpoints (07/02 §4): every finished task = one commit (a content hash); a failed
task rolls back to the commit before it. Snapshots are kept in memory and, with `checkpoint_dir`, as
JSON files, so a killed run can be resumed. With `root`, files are mirrored to disk (only under root).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .validate import is_safe_path


class WorkspaceError(ValueError):
    pass


def files_hash(files: dict[str, str]) -> str:
    h = hashlib.sha256()
    for path in sorted(files):
        h.update(path.encode("utf-8") + b"\0" + files[path].replace("\r\n", "\n").encode("utf-8") + b"\0")
    return h.hexdigest()[:16]


class Workspace:
    def __init__(self, files: dict[str, str] | None = None, *, root: Path | None = None,
                 checkpoint_dir: Path | None = None) -> None:
        self.files: dict[str, str] = {}
        self.root = root.resolve() if root is not None else None
        self.checkpoint_dir = checkpoint_dir
        self._snaps: dict[str, dict[str, str]] = {}
        for p, c in (files or {}).items():
            self.write(p, c)

    def _disk(self, path: str) -> Path | None:
        if self.root is None:
            return None
        target = (self.root / path).resolve()
        if self.root not in target.parents:
            raise WorkspaceError(f"a munkaterületen kívüli út: {path}")
        return target

    def write(self, path: str, content: str) -> None:
        if not is_safe_path(path):
            raise WorkspaceError(f"érvénytelen útvonal: {path}")
        self.files[path] = content
        if (target := self._disk(path)) is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")

    def read(self, path: str) -> str | None:
        return self.files.get(path)

    def view(self, paths: list[str] | tuple[str, ...] | None = None) -> dict[str, str]:
        """A copy (the step runner never writes the workspace directly)."""
        if paths is None:
            return dict(self.files)
        return {p: self.files[p] for p in paths if p in self.files}

    def commit(self) -> str:
        sha = files_hash(self.files)
        self._snaps[sha] = dict(self.files)
        if self.checkpoint_dir is not None:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            (self.checkpoint_dir / f"{sha}.json").write_text(json.dumps(self.files, ensure_ascii=False),
                                                            encoding="utf-8")
        return sha

    def _snapshot(self, sha: str) -> dict[str, str]:
        if sha in self._snaps:
            return self._snaps[sha]
        if self.checkpoint_dir is not None and (p := self.checkpoint_dir / f"{sha}.json").exists():
            snap = json.loads(p.read_text(encoding="utf-8"))
            self._snaps[sha] = snap
            return snap
        raise WorkspaceError(f"ismeretlen checkpoint: {sha}")

    def reset(self, sha: str) -> None:
        """Back to a commit: files added since are removed, changed ones restored."""
        snap = self._snapshot(sha)
        for path in [p for p in self.files if p not in snap]:
            del self.files[path]
            if (target := self._disk(path)) is not None and target.exists():
                target.unlink()
        for path, content in snap.items():
            if self.files.get(path) != content:
                self.write(path, content)
