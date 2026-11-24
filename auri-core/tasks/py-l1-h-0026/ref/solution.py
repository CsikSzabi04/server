# AURI-CANARY-06fa3143-1beb-5ab8-bea5-bd2f8a01e44b
# Reference solution: only for validating the task.
def csv_sor(s):
    out, i, n = [], 0, len(s)
    while True:
        if i < n and s[i] == '"':
            i += 1
            buf = []
            while True:
                if i >= n:
                    raise ValueError('lezáratlan idézőjel')
                if s[i] == '"':
                    if i + 1 < n and s[i + 1] == '"':
                        buf.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                buf.append(s[i])
                i += 1
            if i < n and s[i] != ',':
                raise ValueError('szöveg a záró idézőjel után')
            out.append(''.join(buf))
        else:
            j = s.find(',', i)
            j = n if j < 0 else j
            if '"' in s[i:j]:
                raise ValueError('idézőjel a mezőben')
            out.append(s[i:j])
            i = j
        if i >= n:
            return out
        i += 1
