# AURI-CANARY-d9683aef-489e-5c68-98be-c0f3edbba9db
# Reference solution: only for validating the task.
import re


def datum(s):
    m = re.fullmatch(r'(\d{4})\. ?(\d{1,2})\. ?(\d{1,2})\.', s)
    if not m:
        raise ValueError(s)
    y, mo, d = map(int, m.groups())
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if not 1 <= mo <= 12 or not 1 <= d <= days[mo - 1]:
        raise ValueError(s)
    return (y, mo, d)
