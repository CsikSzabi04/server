# AURI-CANARY-f655c0fe-1e8d-5c67-9f7a-ae957f5d4dd9
# Reference solution: only for validating the task.
def camel_snake(s):
    return ''.join(('_' + c.lower()) if i and c.isupper() else c.lower() if i == 0 else c for i, c in enumerate(s))
