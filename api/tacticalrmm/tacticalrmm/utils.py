from rest_framework import status
from rest_framework.response import Response
import random
import string

notify_error = lambda msg: Response(msg, status=status.HTTP_400_BAD_REQUEST)

def get_random_string(length):
    # Random string with the combination of lower and upper case
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))
    