from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django.http import FileResponse
import os


class ServeFile(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid, file_name):
        file_path = os.path.join(
            "/rmm/api/tacticalrmm/tacticalrmm/private/assets/", file_name
        )

        if not os.path.exists(file_path):
            return Response({"error": "File does not exist"}, status=404)

        return FileResponse(open(file_path, "rb"))
