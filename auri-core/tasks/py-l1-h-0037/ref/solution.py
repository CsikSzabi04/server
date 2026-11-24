# AURI-CANARY-f77963f6-172d-543e-aa1c-c364aafb8467
# Reference solution: only for validating the task.
def egyensuly_index(xs):
    bal, ossz = 0, sum(xs)
    for i, x in enumerate(xs):
        if bal == ossz - bal - x:
            return i
        bal += x
    return -1
