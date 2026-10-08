import time

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from branding.images import MAX_SIZE, detect_image_type, validate_image
from branding.models import BrandingSettings, get_branding
from tacticalrmm.test import TacticalTestCase

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32
ICO = b"\x00\x00\x01\x00\x01\x00" + b"\x00" * 32
SVG = (
    b'\xef\xbb\xbf<?xml version="1.0"?>\n<!-- made by hand -->\n'
    b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
)
HTML = b"<!DOCTYPE html><html><script>alert(1)</script></html>"


class TestBrandingModel(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()

    def test_get_branding_without_row_returns_defaults(self):
        branding = get_branding()
        self.assertIsNone(branding.pk)
        self.assertEqual(branding.product_name, "")
        self.assertEqual(branding.primary, "")
        self.assertFalse(branding.has_image("logo"))
        self.assertEqual(branding.version, 0)

    def test_get_branding_returns_saved_row(self):
        BrandingSettings.objects.create(product_name="ACME")
        self.assertEqual(get_branding().product_name, "ACME")

    def test_only_one_instance(self):
        BrandingSettings.objects.create()
        with self.assertRaises(ValidationError):
            BrandingSettings.objects.create()

    def test_version_changes_on_save(self):
        branding = BrandingSettings.objects.create()
        first = branding.version
        self.assertGreater(first, 0)
        time.sleep(0.01)  # version has millisecond resolution
        branding.product_name = "ACME"
        branding.save()
        self.assertGreater(branding.version, first)


class TestImageValidation(SimpleTestCase):
    def test_detect_types(self):
        self.assertEqual(detect_image_type(PNG), "image/png")
        self.assertEqual(detect_image_type(JPEG), "image/jpeg")
        self.assertEqual(detect_image_type(WEBP), "image/webp")
        self.assertEqual(detect_image_type(ICO), "image/x-icon")
        self.assertEqual(detect_image_type(SVG), "image/svg+xml")
        self.assertIsNone(detect_image_type(HTML))
        self.assertIsNone(detect_image_type(b"GIF89a"))

    def test_allowed_per_kind(self):
        self.assertEqual(validate_image("logo", SVG), "image/svg+xml")
        self.assertEqual(validate_image("favicon", ICO), "image/x-icon")
        self.assertEqual(validate_image("login_background", JPEG), "image/jpeg")

    def test_rejects_wrong_type_for_kind(self):
        with self.assertRaises(ValueError):
            validate_image("login_background", SVG)
        with self.assertRaises(ValueError):
            validate_image("logo", ICO)
        with self.assertRaises(ValueError):
            validate_image("favicon", JPEG)

    def test_rejects_disguised_and_empty(self):
        with self.assertRaises(ValueError):
            validate_image("logo", HTML)
        with self.assertRaises(ValueError):
            validate_image("logo", b"")

    def test_rejects_oversize(self):
        too_big = PNG + b"\x00" * MAX_SIZE["logo"]
        with self.assertRaises(ValueError):
            validate_image("logo", too_big)
        # the background limit is larger than the logo limit
        self.assertEqual(
            validate_image("login_background", PNG + b"\x00" * MAX_SIZE["logo"]),
            "image/png",
        )
