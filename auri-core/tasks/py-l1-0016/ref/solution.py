# AURI-CANARY-f88066e7-2679-52b2-b839-ca66b8c50f80
# Reference solution: only for validating the task.
def snake_camel(s):
    p = [x for x in s.split('_') if x]
    return (p[0].lower() + ''.join(x.capitalize() for x in p[1:])) if p else ''
