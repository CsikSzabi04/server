# AURI-CANARY-c8234c43-0796-5f72-b68d-b84c1a304632
# Reference solution: only for validating the task.
import math


def lnko_lista(xs):
    if not xs:
        raise ValueError('üres')
    return math.gcd(*xs)
