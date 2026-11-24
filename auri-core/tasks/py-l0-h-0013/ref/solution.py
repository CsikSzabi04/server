# AURI-CANARY-ed5e3313-4689-570f-98ed-f9fe79dfae67
# Reference solution: only for validating the task.
def binaris(n):
    if n < 0:
        raise ValueError(n)
    return format(n, 'b')
