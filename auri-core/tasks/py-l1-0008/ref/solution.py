# AURI-CANARY-73b5bca8-862b-59ef-bee9-ad7bd048a729
# Reference solution: only for validating the task.
def kilapit(xs):
    out = []
    for x in xs:
        if isinstance(x, list):
            out.extend(kilapit(x))
        else:
            out.append(x)
    return out
