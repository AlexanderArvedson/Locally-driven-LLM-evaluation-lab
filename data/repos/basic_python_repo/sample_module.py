# This is a sample Python module that contains a helper function, 
# a UserService class with a method to create a user, and a function to build a report based on a list of users.

# The helper function takes a value and returns it with leading and trailing whitespace removed.
def helper(value):
    return value.strip()

# The UserService class contains a method to create a user by calling the helper function with the provided name.
class UserService:
    def create_user(self, name):
        return helper(name)

# The build_report function takes a list of users and returns the number of users in the list.
def build_report(users):
    return len(users)
