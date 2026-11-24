"""Skills (AI-2, spec 5.6): `skills/<name>/SKILL.md` — YAML frontmatter (name, description,
triggers) + an instruction body. Progressive loading: only name + one-line description go
into the static prompt prefix; the body is loaded into the dynamic tail when a trigger
phrase matches (router) or the LLM asks for it (`use_skill`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from rapidfuzz import fuzz

from ..mind.hu_text import norm

MAX_ROUTER_WORDS = 10  # a trigger inside a long sentence is not a skill request


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    triggers: tuple[str, ...]
    body: str


def _parse(path: Path) -> Skill | None:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not m:
        return None
    meta = yaml.safe_load(m.group(1)) or {}
    name = str(meta.get("name") or path.parent.name).strip()
    if not name:
        return None
    return Skill(
        name=name,
        description=" ".join(str(meta.get("description") or "").split()),
        triggers=tuple(norm(t) for t in meta.get("triggers") or [] if t),
        body=m.group(2).strip(),
    )


@dataclass
class SkillBook:
    skills: dict[str, Skill]

    @classmethod
    def load(cls, root: Path) -> SkillBook:
        out: dict[str, Skill] = {}
        if root.is_dir():
            for p in sorted(root.glob("*/SKILL.md")):
                s = _parse(p)
                if s is not None:
                    out[s.name] = s
        return cls(out)

    def index(self) -> list[tuple[str, str]]:
        return sorted((s.name, s.description) for s in self.skills.values())

    def get(self, name: str) -> Skill | None:
        if name in self.skills:
            return self.skills[name]
        n = norm(name).replace(" ", "-")
        best = max(self.skills.values(), key=lambda s: fuzz.ratio(n, norm(s.name)), default=None)
        return best if best is not None and fuzz.ratio(n, norm(best.name)) >= 80 else None

    def route(self, text: str) -> Skill | None:
        """Trigger phrase as whole words in a short utterance → that skill."""
        t = norm(text)
        if len(t.split()) > MAX_ROUTER_WORDS:
            return None
        for s in self.skills.values():
            for trig in s.triggers:
                if re.search(rf"(?:^|\s){re.escape(trig)}(?:\s|$)", t):
                    return s
        return None
