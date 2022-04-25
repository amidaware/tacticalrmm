from rest_framework import status
from rest_framework.response import Response


def notify_error(msg: str) -> Response:
    return Response(msg, status=status.HTTP_400_BAD_REQUEST)
