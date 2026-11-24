# AURI-CANARY-bae43364-2374-5789-891e-859f0311637c
# Reference solution: only for validating the task.
import re

ORDER = {'h': (0, 3600), 'm': (1, 60), 's': (2, 1)}


def idotartam_mp(s):
    total, last = 0, -1
    for part in s.split(' '):
        m = re.fullmatch(r'(\d+)([hms])', part)
        if not m or ORDER[m.group(2)][0] <= last:
            raise ValueError(s)
        last, mult = ORDER[m.group(2)]
        total += int(m.group(1)) * mult
    return total
