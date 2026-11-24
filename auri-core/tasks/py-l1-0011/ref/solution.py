# AURI-CANARY-49536514-79da-5829-b792-d05fcb8358b8
# Reference solution: only for validating the task.
def osszefesul(a, b):
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            out.append(a[i])
            i += 1
        else:
            out.append(b[j])
            j += 1
    return out + a[i:] + b[j:]
