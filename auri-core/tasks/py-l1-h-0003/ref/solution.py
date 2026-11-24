# AURI-CANARY-9cd25317-5484-5122-92fc-a966adb0b6d2
# Reference solution: only for validating the task.
DIG = '0123456789abcdefghijklmnopqrstuvwxyz'


def szamrendszerbol(s, b):
    if not 2 <= b <= 36 or not s:
        raise ValueError((s, b))
    n = 0
    for c in s.lower():
        d = DIG.find(c)
        if d < 0 or d >= b:
            raise ValueError(s)
        n = n * b + d
    return n
