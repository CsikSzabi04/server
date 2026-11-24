# AURI-CANARY-d39871a9-abea-50ed-aa5e-c7cd2e5100fb
# Reference solution: only for validating the task.
import re


def telefonszam(s):
    t = re.sub(r'[ \-/()]', '', s)
    m = re.fullmatch(r'(?:\+36|36|06)(\d{9})', t)
    if not m:
        raise ValueError(s)
    return '+36' + m.group(1)
