import time

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext

from branding.images import MAX_SIZE, detect_image_type, validate_image
from branding.models import BrandingSettings, get_branding
from logs.models import AuditLog
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

    def test_detect_whitespace_flood_is_fast(self):
        # nested quantifiers in the svg regex would backtrack exponentially here
        start = time.monotonic()
        self.assertIsNone(detect_image_type(b" " * 4096 + b"x"))
        self.assertIsNone(detect_image_type(b" \n" * 2048 + b"<html>"))
        # a comment must not be able to swallow the following ones
        self.assertIsNone(detect_image_type(b"<!---->" * 580 + b"x"))
        self.assertLess(time.monotonic() - start, 1)
        self.assertEqual(
            detect_image_type(b"<!-- a - b --><!-- c --><svg></svg>"), "image/svg+xml"
        )

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


def upload(name, content):
    return {"file": SimpleUploadedFile(name, content)}


class TestBrandingPublic(TacticalTestCase):
    def setUp(self):
        self.setup_client()
        self.setup_coresettings()

    def test_get_defaults_unauthenticated(self):
        r = self.client.get("/branding/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["product_name"], "")
        self.assertEqual(r.data["primary"], "")
        self.assertFalse(r.data["has_logo"])
        self.assertEqual(r.data["version"], 0)

    def test_get_with_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token invalid")
        self.assertEqual(self.client.get("/branding/").status_code, 200)
        self.assertEqual(self.client.get("/branding/image/logo/").status_code, 404)

    def test_image_not_set_and_unknown_kind(self):
        self.assertEqual(self.client.get("/branding/image/logo/").status_code, 404)
        self.assertEqual(self.client.get("/branding/image/evil/").status_code, 404)

    def test_writes_need_auth(self):
        self.check_not_authenticated("put", "/branding/")
        self.check_not_authenticated("put", "/branding/image/logo/")
        self.check_not_authenticated("delete", "/branding/image/logo/")


class TestBrandingEdit(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_put_name_and_colors(self):
        data = {"product_name": "ACME RMM", "primary": "#112233", "header": "#ffeb3b"}
        r = self.client.put("/branding/", data, format="json")
        self.assertEqual(r.status_code, 200)
        branding = BrandingSettings.objects.get()
        self.assertEqual(branding.product_name, "ACME RMM")
        self.assertEqual(branding.primary, "#112233")
        self.assertEqual(branding.header, "#ffeb3b")

    def test_put_resets_color_with_empty_string(self):
        self.client.put("/branding/", {"primary": "#112233"}, format="json")
        r = self.client.put("/branding/", {"primary": ""}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(BrandingSettings.objects.get().primary, "")

    def test_put_invalid_color(self):
        for value in ("red", "#12345", "#1234567", "112233"):
            r = self.client.put("/branding/", {"primary": value}, format="json")
            self.assertEqual(r.status_code, 400, value)

    def test_upload_get_delete_image(self):
        r = self.client.put(
            "/branding/image/logo/", upload("logo.jpg", PNG), format="multipart"
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["has_logo"])
        version = r.data["version"]

        r = self.client.get("/branding/image/logo/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, PNG)
        self.assertEqual(r["Content-Type"], "image/png")
        self.assertEqual(r["Cache-Control"], "public, max-age=86400")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

        time.sleep(0.01)  # version has millisecond resolution
        r = self.client.put(
            "/branding/image/logo/", upload("logo.png", JPEG), format="multipart"
        )
        self.assertGreater(r.data["version"], version)

        r = self.client.delete("/branding/image/logo/")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["has_logo"])
        self.assertEqual(self.client.get("/branding/image/logo/").status_code, 404)

    def test_svg_served_with_csp(self):
        self.client.put(
            "/branding/image/logo/", upload("logo.svg", SVG), format="multipart"
        )
        r = self.client.get("/branding/image/logo/")
        self.assertEqual(r["Content-Type"], "image/svg+xml")
        self.assertEqual(
            r["Content-Security-Policy"],
            "default-src 'none'; style-src 'unsafe-inline'",
        )

    def test_upload_rejections(self):
        r = self.client.put(
            "/branding/image/logo/", upload("logo.png", HTML), format="multipart"
        )
        self.assertEqual(r.status_code, 400)
        r = self.client.put(
            "/branding/image/login_background/",
            upload("bg.svg", SVG),
            format="multipart",
        )
        self.assertEqual(r.status_code, 400)
        too_big = PNG + b"\x00" * MAX_SIZE["logo"]
        r = self.client.put(
            "/branding/image/logo/", upload("logo.png", too_big), format="multipart"
        )
        self.assertEqual(r.status_code, 400)
        r = self.client.put("/branding/image/logo/", {}, format="multipart")
        self.assertEqual(r.status_code, 400)
        r = self.client.put(
            "/branding/image/evil/", upload("logo.png", PNG), format="multipart"
        )
        self.assertEqual(r.status_code, 404)
        self.assertFalse(BrandingSettings.objects.filter(logo__isnull=False).exists())

    def test_delete_without_row(self):
        r = self.client.delete("/branding/image/favicon/")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(BrandingSettings.objects.exists())

    def test_permissions(self):
        view_only = self.create_user_with_roles(["can_view_core_settings"])
        self.client.force_authenticate(user=view_only)
        self.check_not_authorized("put", "/branding/", {"product_name": "x"})
        r = self.client.put(
            "/branding/image/logo/", upload("logo.png", PNG), format="multipart"
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.delete("/branding/image/logo/").status_code, 403)

        editor = self.create_user_with_roles(["can_edit_core_settings"])
        self.client.force_authenticate(user=editor)
        r = self.client.put("/branding/", {"product_name": "x"}, format="json")
        self.assertEqual(r.status_code, 200)


class TestBrandingEfficiencyAndAudit(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()
        for kind, content in (
            ("logo", PNG),
            ("favicon", ICO),
            ("login_background", JPEG),
        ):
            self.client.put(
                f"/branding/image/{kind}/",
                upload(f"{kind}.bin", content),
                format="multipart",
            )

    def selected_sql(self, url):
        self.client.logout()
        with CaptureQueriesContext(connection) as ctx:
            r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        return " ".join(
            q["sql"] for q in ctx.captured_queries if "branding" in q["sql"]
        )

    def test_config_read_does_not_load_images(self):
        sql = self.selected_sql("/branding/")
        self.assertTrue(sql)
        for column in ('"logo"', '"favicon"', '"login_background"'):
            self.assertNotIn(column, sql)

    def test_image_read_loads_only_that_image(self):
        sql = self.selected_sql("/branding/image/logo/")
        self.assertIn('"logo"', sql)
        self.assertNotIn('"favicon"', sql)
        self.assertNotIn('"login_background"', sql)

    def test_replacing_an_image_is_audited(self):
        before = AuditLog.objects.filter(object_type="brandingsettings").count()
        r = self.client.put(
            "/branding/image/logo/", upload("logo.png", PNG + b""), format="multipart"
        )
        self.assertEqual(r.status_code, 200)
        entries = AuditLog.objects.filter(object_type="brandingsettings")
        self.assertEqual(entries.count(), before + 1)
        latest = entries.latest("pk")
        self.assertNotEqual(
            latest.before_value["logo_sha256"], latest.after_value["logo_sha256"]
        )
