import time

from django.core.exceptions import ValidationError

from branding.models import BrandingSettings, get_branding
from tacticalrmm.test import TacticalTestCase


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
