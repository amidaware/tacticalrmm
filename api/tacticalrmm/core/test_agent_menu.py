from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from core.agent_menu import effective_agent_menu_layout, validate_agent_menu_layout


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
