# AURI-CANARY-660c5b1a-dd4a-566b-95b3-c9b03d6e281c
# Reference solution: only for validating the task.
def statisztika(s):
    d = {'betu': 0, 'szamjegy': 0, 'szokoz': 0, 'egyeb': 0}
    for c in s:
        d['betu' if c.isalpha() else 'szamjegy' if c.isdigit() else 'szokoz' if c.isspace() else 'egyeb'] += 1
    return d
