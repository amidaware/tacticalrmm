from django.http import Http404, HttpResponse
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from tacticalrmm.helpers import notify_error

from .images import MAX_SIZE, validate_image
from .models import IMAGE_KINDS, get_branding
from .permissions import BrandingPerms
from .serializers import BrandingSerializer

IMAGE_CSP = "default-src 'none'; style-src 'unsafe-inline'"


class PublicReadView(APIView):
    permission_classes = [BrandingPerms]

    def get_authenticators(self):
        # skip token auth for reads, so a stale token on the login page does not cause a 401
        if self.request.method in SAFE_METHODS:
            return []
        return super().get_authenticators()


class GetEditBranding(PublicReadView):
    def get(self, request):
        return Response(BrandingSerializer(get_branding()).data)

    def put(self, request):
        serializer = BrandingSerializer(
            instance=get_branding(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class BrandingImage(PublicReadView):
    parser_classes = [MultiPartParser]

    def get(self, request, kind):
        if kind not in IMAGE_KINDS:
            raise Http404

        branding = get_branding()
        data = getattr(branding, kind)
        if not data:
            raise Http404

        response = HttpResponse(
            bytes(data), content_type=getattr(branding, f"{kind}_type")
        )
        response["Cache-Control"] = "public, max-age=86400"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = IMAGE_CSP
        return response

    def put(self, request, kind):
        if kind not in IMAGE_KINDS:
            raise Http404

        upload = request.FILES.get("file")
        if upload is None:
            return notify_error("No file uploaded.")

        data = upload.read(MAX_SIZE[kind] + 1)
        try:
            mime = validate_image(kind, data)
        except ValueError as e:
            return notify_error(str(e))

        branding = get_branding()
        setattr(branding, kind, data)
        setattr(branding, f"{kind}_type", mime)
        branding.save()
        return Response(BrandingSerializer(branding).data)

    def delete(self, request, kind):
        if kind not in IMAGE_KINDS:
            raise Http404

        branding = get_branding()
        if branding.pk:
            setattr(branding, kind, None)
            setattr(branding, f"{kind}_type", "")
            branding.save()
        return Response(BrandingSerializer(branding).data)
