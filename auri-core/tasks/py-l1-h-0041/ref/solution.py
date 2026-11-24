# AURI-CANARY-de864572-4bf2-5dec-b9d2-9456db8b961e
# Reference solution: only for validating the task.
def median(xs):
    if not xs:
        raise ValueError('üres')
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
