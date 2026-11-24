# AURI-CANARY-8f305171-cdb0-548f-b497-5a934452c79e
# Reference solution: only for validating the task.
def csucsok(xs):
    n = len(xs)
    return [i for i in range(n) if (i == 0 or xs[i] > xs[i - 1]) and (i == n - 1 or xs[i] > xs[i + 1])]
