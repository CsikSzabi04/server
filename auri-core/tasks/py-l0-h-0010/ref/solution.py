# AURI-CANARY-98fac19d-ee36-5ca2-b169-d95cc2c21b50
# Reference solution: only for validating the task.
def leghosszabb_szo(s):
    return max(s.split(), key=len, default='')
