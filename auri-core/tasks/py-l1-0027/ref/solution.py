# AURI-CANARY-8e6bc047-3624-5673-839e-79ec01a97caa
# Reference solution: only for validating the task.
def sortores(szoveg, szelesseg):
    if szelesseg < 1:
        raise ValueError(szelesseg)
    sorok, cur = [], ''
    for w in szoveg.split():
        if cur and len(cur) + 1 + len(w) <= szelesseg:
            cur += ' ' + w
        else:
            if cur:
                sorok.append(cur)
            cur = w
    if cur:
        sorok.append(cur)
    return sorok
