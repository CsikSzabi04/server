# AURI-CANARY-109efaad-7a66-5032-841f-886c17f01c0d
# Reference solution: only for validating the task.
import datetime

NEVEK = ['hétfő', 'kedd', 'szerda', 'csütörtök', 'péntek', 'szombat', 'vasárnap']


def het_napja(ev, ho, nap):
    return NEVEK[datetime.date(ev, ho, nap).weekday()]
