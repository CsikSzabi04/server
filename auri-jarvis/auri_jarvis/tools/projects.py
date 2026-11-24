"""Git status of the allowlisted projects (AI-2): only repos directly under
`tools.projects_root` (spec 5.6). Fixed argv, no shell, short timeouts. Blocking — call it
from a worker thread."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz

from ..mind.hu_text import norm


@dataclass(frozen=True)
class RepoStatus:
    name: str
    branch: str
    changed: int
    subject: str
    rel: str  # "2 days ago" (git's relative date)

    def sentence(self) -> str:
        s = f"{self.name}: {self.branch} ág, {self.changed} módosított fájl."
        if self.subject:
            s += f" Utolsó commit {self.rel}: {self.subject}."
        return s


def list_repos(root: Path | None) -> list[Path]:
    """Repos under root, most recently touched first."""
    if root is None or not root.is_dir():
        return []
    repos = [d for d in root.iterdir() if d.is_dir() and (d / ".git").exists()]
    return sorted(repos, key=lambda d: (d / ".git").stat().st_mtime, reverse=True)


def find_repo(root: Path | None, name: str) -> Path | None:
    repos = list_repos(root)
    if not repos:
        return None
    score, path = max(((fuzz.WRatio(norm(name), norm(d.name)), d) for d in repos), key=lambda x: x[0])
    return path if score >= 80 else None


def _git(path: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return out.stdout.strip()


def repo_status(path: Path) -> RepoStatus:
    status = _git(path, "status", "--porcelain=v1", "-b").splitlines()
    branch = status[0][3:].split("...")[0] if status and status[0].startswith("##") else "?"
    changed = len([ln for ln in status[1:] if ln.strip()])
    subject, rel = [*_git(path, "log", "-1", "--format=%s\x1f%cr").split("\x1f"), "", ""][:2]
    return RepoStatus(path.name, branch, changed, subject, rel)
