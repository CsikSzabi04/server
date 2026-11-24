# AURI-CANARY-0e97ffe8-0973-5f10-a001-5832a1068249
# Reference solution: only for validating the task.
def haromszog(a, b, c):
    return min(a, b, c) > 0 and a + b > c and a + c > b and b + c > a
