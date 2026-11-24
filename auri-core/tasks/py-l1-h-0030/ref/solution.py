# AURI-CANARY-c871a4fc-9c6e-5127-ae3e-573045c61376
# Reference solution: only for validating the task.
import re


def rpn(kif):
    st = []
    for t in kif.split():
        if re.fullmatch(r'-?[0-9]+', t):
            st.append(int(t))
        elif t in ('+', '-', '*'):
            if len(st) < 2:
                raise ValueError('kevés operandus')
            b, a = st.pop(), st.pop()
            st.append(a + b if t == '+' else a - b if t == '-' else a * b)
        else:
            raise ValueError(t)
    if len(st) != 1:
        raise ValueError('nem egy érték maradt')
    return st[0]
