from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from accounts.models import User
from core.agent_menu import effective_agent_menu_layout, validate_agent_menu_layout
from core.models import CoreSettings
from tacticalrmm.test import TacticalTestCase

LAYOUT = {"order": ["run_script", "take_control"], "hidden": ["vnc"]}


class TestValidateAgentMenuLayout(SimpleTestCase):
    def test_valid(self):
        for value in (
            {},
            {"order": []},
            {"hidden": ["vnc"]},
            {"order": ["take_control", "run_script"], "hidden": ["vnc"]},
            {"order": [f"item_{i}" for i in range(100)]},
        ):
            validate_agent_menu_layout(value)

    def test_invalid(self):
        for value in (
            [],
            "x",
            None,
            {"order": "take_control"},
            {"order": ["a", "a"]},
            {"order": ["Take Control"]},
            {"order": [""]},
            {"order": ["a" * 51]},
            {"order": [1]},
            {"other": []},
            {"order": [f"item_{i}" for i in range(101)]},
        ):
            with self.assertRaises(ValidationError, msg=repr(value)):
                validate_agent_menu_layout(value)


class TestEffectiveAgentMenuLayout(SimpleTestCase):
    company = {"order": ["run_script"]}
    user = {"order": ["vnc"]}

    def test_user_layout_when_allowed(self):
        self.assertEqual(
            effective_agent_menu_layout(self.user, self.company, True), self.user
        )

    def test_company_layout_when_user_empty(self):
        self.assertEqual(
            effective_agent_menu_layout({}, self.company, True), self.company
        )

    def test_company_layout_when_locked(self):
        self.assertEqual(
            effective_agent_menu_layout(self.user, self.company, False), self.company
        )

    def test_defaults(self):
        self.assertEqual(effective_agent_menu_layout({}, {}, True), {})
        self.assertEqual(effective_agent_menu_layout(None, None, True), {})


class TestAgentMenuSettings(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_core_settings_accepts_layout(self):
        r = self.client.put(
            "/core/settings/",
            {"agent_menu_layout": LAYOUT, "agent_menu_allow_user": False},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        core = CoreSettings.objects.first()
        self.assertEqual(core.agent_menu_layout, LAYOUT)
        self.assertFalse(core.agent_menu_allow_user)

    def test_core_settings_defaults(self):
        core = CoreSettings.objects.first()
        self.assertEqual(core.agent_menu_layout, {})
        self.assertTrue(core.agent_menu_allow_user)

    def test_core_settings_rejects_invalid_layout(self):
        r = self.client.put(
            "/core/settings/", {"agent_menu_layout": {"order": ["A B"]}}, format="json"
        )
        self.assertEqual(r.status_code, 400)

    def test_user_ui_accepts_layout(self):
        r = self.client.patch(
            "/accounts/users/ui/", {"agent_menu_layout": LAYOUT}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(User.objects.get(pk=self.john.pk).agent_menu_layout, LAYOUT)

    def test_user_ui_rejects_invalid_layout(self):
        r = self.client.patch(
            "/accounts/users/ui/", {"agent_menu_layout": {"order": "x"}}, format="json"
        )
        self.assertEqual(r.status_code, 400)


class TestAgentMenuDashInfo(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()
        self.core = CoreSettings.objects.first()

    def dashinfo(self):
        r = self.client.get("/core/dashinfo/")
        self.assertEqual(r.status_code, 200)
        return r.data

    def set_company(self, layout, allow=True):
        self.core.agent_menu_layout = layout
        self.core.agent_menu_allow_user = allow
        self.core.save()

    def test_defaults(self):
        data = self.dashinfo()
        self.assertEqual(data["agent_menu_layout"], {})
        self.assertTrue(data["agent_menu_allow_user"])
        self.assertEqual(data["agent_menu_user_layout"], {})

    def test_company_layout(self):
        self.set_company(LAYOUT)
        self.assertEqual(self.dashinfo()["agent_menu_layout"], LAYOUT)

    def test_user_override(self):
        self.set_company(LAYOUT)
        self.john.agent_menu_layout = {"order": ["vnc"]}
        self.john.save()
        data = self.dashinfo()
        self.assertEqual(data["agent_menu_layout"], {"order": ["vnc"]})
        self.assertEqual(data["agent_menu_user_layout"], {"order": ["vnc"]})
        # Preferences needs the company layout to offer "use company default"
        self.assertEqual(data["agent_menu_company_layout"], LAYOUT)

    def test_locked_uses_company_and_keeps_user_layout(self):
        self.set_company(LAYOUT, allow=False)
        self.john.agent_menu_layout = {"order": ["vnc"]}
        self.john.save()
        data = self.dashinfo()
        self.assertEqual(data["agent_menu_layout"], LAYOUT)
        self.assertFalse(data["agent_menu_allow_user"])
        self.assertEqual(data["agent_menu_user_layout"], {"order": ["vnc"]})
        self.set_company(LAYOUT, allow=True)
        self.assertEqual(self.dashinfo()["agent_menu_layout"], {"order": ["vnc"]})

    def test_user_without_settings_permission_gets_company_layout(self):
        self.set_company(LAYOUT)
        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)
        self.assertEqual(self.dashinfo()["agent_menu_layout"], LAYOUT)
