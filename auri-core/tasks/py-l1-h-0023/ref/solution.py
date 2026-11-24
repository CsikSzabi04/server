# AURI-CANARY-5615f8b7-6077-57be-9bc4-5d3c35bda032
# Reference solution: only for validating the task.
EGY = ['', 'egy', 'kettő', 'három', 'négy', 'öt', 'hat', 'hét', 'nyolc', 'kilenc']
TIZ = ['', 'tíz', 'húsz', 'harminc', 'negyven', 'ötven', 'hatvan', 'hetven', 'nyolcvan', 'kilencven']
KOT = ['', 'tizen', 'huszon', *TIZ[3:]]


def szam_betuvel(n):
    if not 0 <= n <= 99:
        raise ValueError(n)
    if n == 0:
        return 'nulla'
    t, e = divmod(n, 10)
    return TIZ[t] if e == 0 else KOT[t] + EGY[e]
