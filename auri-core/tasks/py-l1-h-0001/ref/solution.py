# AURI-CANARY-46234616-18ea-547a-9fca-3314136ba8cf
# Reference solution: only for validating the task.
def caesar(s, k):
    out = []
    for c in s:
        if 'a' <= c <= 'z':
            out.append(chr((ord(c) - 97 + k) % 26 + 97))
        elif 'A' <= c <= 'Z':
            out.append(chr((ord(c) - 65 + k) % 26 + 65))
        else:
            out.append(c)
    return ''.join(out)
