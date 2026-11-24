# AURI-CANARY-80f401a2-d116-56f1-83e5-d80695bcc180
# Reference solution: only for validating the task.
def szamjegyosszeg(n):
    return sum(int(d) for d in str(abs(n)))
