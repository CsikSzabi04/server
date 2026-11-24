# AURI-CANARY-c5e0444b-461a-55fb-84d8-80fa89ead877
# Reference solution: only for validating the task.
def pascal_sor(n):
    if n < 0:
        raise ValueError(n)
    row = [1]
    for _ in range(n):
        row = [a + b for a, b in zip([0, *row], [*row, 0], strict=True)]
    return row
