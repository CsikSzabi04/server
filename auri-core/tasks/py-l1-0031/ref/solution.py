# AURI-CANARY-87ec13c6-605e-5216-a596-0d7d683425d9
# Reference solution: only for validating the task.
def maganhangzok(s):
    return sum(c in 'aáeéiíoóöőuúüű' for c in s.lower())
