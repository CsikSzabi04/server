# AURI-CANARY-3380e876-a0bb-5a01-b389-a47c7cc227bb
# Reference solution: only for validating the task.
def honap_napjai(ev, ho):
    if not 1 <= ho <= 12:
        raise ValueError(ho)
    if ho == 2:
        return 29 if ev % 4 == 0 and (ev % 100 != 0 or ev % 400 == 0) else 28
    return 30 if ho in (4, 6, 9, 11) else 31
