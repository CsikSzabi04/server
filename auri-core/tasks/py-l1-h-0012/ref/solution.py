# AURI-CANARY-34985e85-6a82-5388-bbed-d878e314cedd
# Reference solution: only for validating the task.
def luhn(s):
    t = s.replace(' ', '')
    if len(t) < 2 or not all('0' <= c <= '9' for c in t):
        return False
    total = 0
    for i, c in enumerate(reversed(t)):
        d = int(c)
        if i % 2 == 1:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0
