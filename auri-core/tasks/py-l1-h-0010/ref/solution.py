# AURI-CANARY-d1e1403d-cb8c-56fc-a626-50e32b0bb214
# Reference solution: only for validating the task.
def _resz(x):
    return x != '' and all('0' <= c <= '9' for c in x) and (x == '0' or x[0] != '0') and int(x) <= 255


def ipv4_ervenyes(s):
    p = s.split('.')
    return len(p) == 4 and all(_resz(x) for x in p)
