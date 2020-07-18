from rest_framework import status
from rest_framework.response import Response

notify_error = lambda msg: Response(msg, status=status.HTTP_400_BAD_REQUEST)
