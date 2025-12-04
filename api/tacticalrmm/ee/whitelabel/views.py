"""
Copyright (c) 2025-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from tacticalrmm.helpers import notify_error
from core.permissions import CoreSettingsPerms
from core.utils import get_core_settings
from tacticalrmm.utils import download_and_extract_webtar


class AddBranding(APIView):
    permission_classes = [IsAuthenticated, CoreSettingsPerms]

    class InputRequest(serializers.Serializer):
        company_name = serializers.CharField(
            max_length=255, required=False, allow_blank=True
        )
        primary_color = serializers.CharField(
            max_length=25, required=False, allow_blank=True
        )
        secondary_color = serializers.CharField(
            max_length=25, required=False, allow_blank=True
        )
        accent_color = serializers.CharField(
            max_length=25, required=False, allow_blank=True
        )
        dark_color = serializers.CharField(
            max_length=25, required=False, allow_blank=True
        )
        dark_page_color = serializers.CharField(
            max_length=25, required=False, allow_blank=True
        )
        positive_color = serializers.CharField(
            max_length=25, required=False, allow_blank=True
        )
        negative_color = serializers.CharField(
            max_length=25, required=False, allow_blank=True
        )
        info_color = serializers.CharField(
            max_length=25, required=False, allow_blank=True
        )
        warning_color = serializers.CharField(
            max_length=25, required=False, allow_blank=True
        )
        favicon = serializers.CharField(required=False, allow_blank=True)

    def get(self, request):
        settings = get_core_settings()
        return Response(settings.branding)

    def post(self, request):
        settings = get_core_settings()

        self.InputRequest(data=request.data).is_valid(raise_exception=True)

        settings.branding = request.data
        settings.save(update_fields=["branding"])

        if settings.DOCKER_BUILD:
            return Response()
        else:
            result = download_and_extract_webtar()
            if not result:
                return notify_error("Failed to download and extract webtar")
            else:
                return Response()
