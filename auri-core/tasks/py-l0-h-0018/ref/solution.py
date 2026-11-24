# AURI-CANARY-18275bc9-b968-5e81-b84b-c8dde2ef2452
# Reference solution: only for validating the task.
def ido_formatum(mp):
    if not 0 <= mp < 86400:
        raise ValueError(mp)
    return f'{mp // 3600:02d}:{mp // 60 % 60:02d}:{mp % 60:02d}'
