# AURI-CANARY-ae11b12d-862c-57f4-af81-d3c99dae5b7a
# Reference solution: only for validating the task.
def kozos(a, b):
    bs = set(b)
    return [x for x in dict.fromkeys(a) if x in bs]
