# AURI-CANARY-4c23fd78-6c31-5e53-bcd8-860b2871a9a4
# Reference solution: only for validating the task.
def atlagon_feluli(xs):
    return [x for x in xs if x * len(xs) > sum(xs)]
