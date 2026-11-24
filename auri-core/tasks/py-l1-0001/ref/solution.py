# Reference solution: only for validating the task (green on visible + hidden tests).
import re

_FORINT = re.compile(r"(-?)([0-9]{1,3}(?:[ \u00a0][0-9]{3})+|[0-9]+) +(?:Ft|HUF)")


def parse_forint(s: str) -> int:
    match = _FORINT.fullmatch(s.strip())
    if match is None:
        raise ValueError(f"érvénytelen forintösszeg: {s!r}")
    sign, digits = match.groups()
    value = int(digits.replace(" ", "").replace("\u00a0", ""))
    return -value if sign else value
