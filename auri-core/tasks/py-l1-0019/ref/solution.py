# AURI-CANARY-6fbf813d-34b7-51eb-8b67-0b4e98de2849
# Reference solution: only for validating the task.
def idotartam_szoveg(mp):
    if mp < 0:
        raise ValueError(mp)
    if mp == 0:
        return '0 másodperc'
    h, r = divmod(mp, 3600)
    m, s = divmod(r, 60)
    return ' '.join(f'{v} {n}' for v, n in ((h, 'óra'), (m, 'perc'), (s, 'másodperc')) if v)
