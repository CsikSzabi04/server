# AURI-CANARY-ce7c4603-dbab-56cc-89af-1bb67f28acae
# Reference solution: only for validating the task.
DIG = '0123456789abcdefghijklmnopqrstuvwxyz'


def szamrendszer(n, b):
    if n < 0 or not 2 <= b <= 36:
        raise ValueError((n, b))
    out = ''
    while True:
        n, r = divmod(n, b)
        out = DIG[r] + out
        if n == 0:
            return out
