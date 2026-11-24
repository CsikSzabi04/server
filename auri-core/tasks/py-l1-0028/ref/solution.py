# AURI-CANARY-d579e180-1824-53ed-857d-fe7a0dff7851
# Reference solution: only for validating the task.
def zarojelek(s):
    st, pair = [], {')': '(', ']': '[', '}': '{'}
    for c in s:
        if c in '([{':
            st.append(c)
        elif c in pair and (not st or st.pop() != pair[c]):
            return False
    return not st
