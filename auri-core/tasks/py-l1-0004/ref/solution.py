# AURI-CANARY-7029c79e-5c99-5446-9c30-d345adc67520
# Reference solution: only for validating the task.
def palindrom(s):
    t = [c.casefold() for c in s if c.isalnum()]
    return t == t[::-1]
