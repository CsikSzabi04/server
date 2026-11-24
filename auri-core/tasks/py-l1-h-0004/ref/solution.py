# AURI-CANARY-2a19792a-5c26-5fdf-a52b-2a54533878ae
# Reference solution: only for validating the task.
def betu_gyakorisag(s):
    d = {}
    for c in s.lower():
        if c.isalpha():
            d[c] = d.get(c, 0) + 1
    return d
