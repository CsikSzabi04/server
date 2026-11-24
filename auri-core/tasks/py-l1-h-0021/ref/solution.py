# AURI-CANARY-35343a44-f007-55ac-8547-2af677805881
# Reference solution: only for validating the task.
import itertools


def permutaciok(s):
    return sorted({''.join(p) for p in itertools.permutations(s)})
