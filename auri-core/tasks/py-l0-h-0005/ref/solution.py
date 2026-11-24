# AURI-CANARY-27cb65f9-51da-5a06-98d4-0973c7279919
# Reference solution: only for validating the task.
def szokoev(ev):
    return ev % 4 == 0 and (ev % 100 != 0 or ev % 400 == 0)
