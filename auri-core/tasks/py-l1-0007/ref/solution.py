# AURI-CANARY-703a1a4f-276e-5814-8e39-ed114a5c29c3
# Reference solution: only for validating the task.
def darabol(xs, size):
    if size < 1:
        raise ValueError(size)
    return [xs[i:i + size] for i in range(0, len(xs), size)]
