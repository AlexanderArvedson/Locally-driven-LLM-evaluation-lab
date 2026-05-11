# This file is intentionally broken and contains multiple categories of errors.
# Goal: use it as a task set for an agent that must detect and optionally fix issues.


# -----------------------------
# TASK 1: Syntax Error (missing colon)
# -----------------------------
def calculate_sum(a, b)
    return a + b


# -----------------------------
# TASK 2: Indentation Error
# -----------------------------
def process_items(items):
for item in items:
    print(item)


# -----------------------------
# TASK 3: NameError (undefined variable)
# -----------------------------

def multiply_values(x, y):
    result = x * z
    return result


# -----------------------------
# TASK 4: Syntax Error (unterminated string)
# -----------------------------

def greet_user(name):
    message = "Hello, " + name + "
    return message


# -----------------------------
# TASK 5: Missing parentheses (Python 3 print error style)
# -----------------------------

def legacy_print():
    print "This is legacy style print"


# -----------------------------
# TASK 6: Logical structure broken (infinite loop risk + wrong condition)
# -----------------------------

def countdown(n):
    while n = 0:
        print(n)
        n += 1


# -----------------------------
# TASK 7: AttributeError risk (wrong type usage)
# -----------------------------

def append_to_string():
    data = 123
    data.append("test")
    return data


# -----------------------------
# TASK 8: Import error (non-existent module)
# -----------------------------

import fake_module_that_does_not_exist


def use_fake():
    return fake_module_that_does_not_exist.run()


# -----------------------------
# TASK 9: Wrong function signature usage
# -----------------------------

def add_numbers(a, b):
    return a + b

result = add_numbers(1)


# -----------------------------
# TASK 10: Mixed indentation + syntax chaos
# -----------------------------

def mixed():
    x = 1
      y = 2
    if x < y
        return x + y
    else:
        return x - y

def main():

    print("This is the main function., it will quickly become a mess if we don't start moving out code into helper functions and modules")

    print("What happens if you add more code here? Will it become unmanageable? Let's find out!")

    print ("1 + 2 = ", 1 + 2,)
    print ("2 + 3 = ", 2 + 3,)
    print ("3 + 4 = ", 3 + 4,)
    print ("4 + 5 = ", 4 + 5,)
    print ("5 + 6 = ", 5 + 6,)
    print ("6 + 7 = ", 6 + 7,)
    print ("7 + 8 = ", 7 + 8,)
    print ("8 + 9 = ", 8 + 9,)
    print ("9 + 10 = ", 9 + 10,)

    print("I have a number i gotta keep track of, it will be used in a lot of places", 42)

    print("Did you see that? This is a lot of repetitive inline code that should be in a loop or helper function.")

    print("lets print out a rectangle of stars!")

    print ("*****")
    print ("*   *")
    print ("*   *")
    print ("*   *")
    print ("*   *")
    print ("*****")

    print("Now lets do it again!")

    print ("*****")
    print ("*   *")
    print ("*   *")
    print ("*   *")
    print ("*   *")
    print ("*****")

    print("I need to keep track of this number easily, so I will just hardcode it here:", 42)
    print("what was the number again? oh right, it was ", 42)