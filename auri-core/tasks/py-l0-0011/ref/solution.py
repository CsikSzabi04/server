# AURI-CANARY-db84fa3c-a13a-5624-a813-020d0e8fac75
# Reference solution: only for validating the task.
def fizzbuzz(n):
    return ['FizzBuzz' if i % 15 == 0 else 'Fizz' if i % 3 == 0 else 'Buzz' if i % 5 == 0 else str(i) for i in range(1, n + 1)]
