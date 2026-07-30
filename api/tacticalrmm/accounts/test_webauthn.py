import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.db import IntegrityError
from django.test import override_settings
from django.utils import timezone as djangotime

from accounts import webauthn_service as wa
from accounts import webauthn_test_vectors as vectors
from accounts.models import User, WebAuthnChallenge, WebAuthnCredential
from accounts.webauthn_views import (
    _PRE_2FA_USER_ID,
    _WEBAUTHN_LOGIN_CHALLENGE,
    _WEBAUTHN_REGISTER_CHALLENGE,
    _WEBAUTHN_REAUTH_CHALLENGE,
    _create_credential,
)
from tacticalrmm.middleware import request_local
from logs.models import AuditLog
from tacticalrmm.constants import AuditActionType
from tacticalrmm.test import TacticalTestCase

LOCALHOST_SETTINGS = {
    "CORS_ORIGIN_WHITELIST": [vectors.LOCALHOST_ORIGIN],
}


def _session_challenge(challenge, *, minutes=5):
    return {
        "challenge": challenge,
        "expires_at": (djangotime.now() + timedelta(minutes=minutes)).isoformat(),
    }


class _FakeUser:
    id = 42
    username = "operator"


@override_settings(
    CORS_ORIGIN_WHITELIST=["https://rmm.example.com"],
    WEBAUTHN_RP_NAME="Tactical RMM Test",
)
class TestWebAuthnService(TacticalTestCase):
    def test_rp_id_and_origin_from_trusted_config(self):
        self.assertEqual(wa.rp_id(), "rmm.example.com")
        self.assertEqual(wa.rp_origin(), "https://rmm.example.com")

    def test_registration_options_have_challenge_and_rp(self):
        opts = wa.registration_options(_FakeUser(), [])
        self.assertTrue(opts.challenge and len(opts.challenge) >= 16)
        self.assertEqual(opts.rp.id, "rmm.example.com")
        self.assertEqual(opts.user.name, "operator")

    def test_registration_cross_platform_hints_hybrid(self):
        opts = wa.registration_options(_FakeUser(), [], attachment="cross-platform")
        body = json.loads(wa.options_to_json(opts))
        self.assertIn("authenticatorSelection", body)
        self.assertEqual(
            body["authenticatorSelection"]["authenticatorAttachment"],
            "cross-platform",
        )
        self.assertEqual(body["hints"], ["hybrid"])

    def test_registration_platform_hints_client_device(self):
        opts = wa.registration_options(_FakeUser(), [], attachment="platform")
        body = json.loads(wa.options_to_json(opts))
        self.assertEqual(body["hints"], ["client-device"])
        self.assertEqual(
            body["authenticatorSelection"]["authenticatorAttachment"], "platform"
        )

    def test_registration_default_hints_all_three(self):
        opts = wa.registration_options(_FakeUser(), [])
        body = json.loads(wa.options_to_json(opts))
        self.assertEqual(
            body["hints"],
            ["client-device", "hybrid", "security-key"],
        )

    def test_registration_resident_key_required(self):
        opts = wa.registration_options(_FakeUser(), [])
        body = json.loads(wa.options_to_json(opts))
        self.assertEqual(body["authenticatorSelection"]["residentKey"], "required")

    def test_registration_user_verification_preferred(self):
        opts = wa.registration_options(_FakeUser(), [])
        body = json.loads(wa.options_to_json(opts))
        self.assertEqual(
            body["authenticatorSelection"]["userVerification"], "preferred"
        )

    def test_authentication_options_have_challenge(self):
        opts = wa.authentication_options([])
        self.assertTrue(opts.challenge and len(opts.challenge) >= 16)
        self.assertEqual(opts.rp_id, "rmm.example.com")

    def test_authentication_options_can_require_user_verification(self):
        opts = wa.authentication_options([], require_user_verification=True)
        body = json.loads(wa.options_to_json(opts))
        self.assertEqual(body["userVerification"], "required")

    def test_authentication_json_is_local_first(self):
        opts = wa.authentication_options([])
        body = json.loads(wa.authentication_options_to_json(opts))
        self.assertEqual(body["hints"], ["client-device", "hybrid", "security-key"])


@override_settings(
    CORS_ORIGIN_WHITELIST=["https://rmm.example.com"],
)
class TestWebAuthnCredentialAudit(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.authenticate()
        self.john.totp_key = "AB5RI6YPFTZAS52G"
        self.john.save()

    def test_serialize_returns_audit_fields(self):
        cred = WebAuthnCredential.objects.create(
            user=self.john,
            credential_id=wa.bytes_to_base64url(b"audit-cred"),
            public_key=b"\x01\x02",
            sign_count=3,
            nickname="Audit Key",
        )
        data = WebAuthnCredential.serialize(cred)
        self.assertEqual(data["username"], "john")
        self.assertEqual(data["nickname"], "Audit Key")
        self.assertEqual(data["sign_count"], 3)
        self.assertNotIn("public_key", data)

    def test_save_with_audit_middleware_username_does_not_crash(self):
        request_local.username = "john"
        try:
            cred = WebAuthnCredential(
                user=self.john,
                credential_id=wa.bytes_to_base64url(b"audit-save-cred"),
                public_key=b"\x03\x04",
                sign_count=0,
                nickname="Saved",
            )
            cred.save()
            self.assertTrue(WebAuthnCredential.objects.filter(pk=cred.pk).exists())
            self.assertTrue(
                AuditLog.objects.filter(
                    username="john",
                    object_type="webauthncredential",
                    action=AuditActionType.ADD,
                ).exists()
            )
        finally:
            request_local.username = None

    @patch("accounts.webauthn_views.WebAuthnCredential.objects.create")
    def test_create_credential_maps_integrity_error(self, mock_create):
        mock_create.side_effect = IntegrityError("duplicate credential_id")
        result = _create_credential(
            self.john,
            credential_id="dup-id",
            public_key=b"\x05",
            sign_count=0,
        )
        self.assertIsNone(result)


@override_settings(**LOCALHOST_SETTINGS)
class TestWebAuthnVerifyService(TacticalTestCase):
    def test_verify_registration_with_official_vector(self):
        verified = wa.verify_registration(
            vectors.REGISTRATION_CREDENTIAL_JSON,
            vectors.REGISTRATION_CHALLENGE_B64,
        )
        self.assertEqual(
            wa.bytes_to_base64url(verified.credential_id),
            vectors.REGISTRATION_CREDENTIAL_ID_B64,
        )
        self.assertTrue(verified.credential_public_key)
        self.assertGreaterEqual(verified.sign_count, 0)

    def test_verify_authentication_updates_sign_count(self):
        result = wa.verify_authentication(
            vectors.AUTHENTICATION_CREDENTIAL_JSON,
            vectors.AUTHENTICATION_CHALLENGE_B64,
            vectors.AUTHENTICATION_PUBLIC_KEY,
            vectors.AUTHENTICATION_SIGN_COUNT,
        )
        self.assertEqual(
            wa.bytes_to_base64url(result.credential_id),
            vectors.AUTHENTICATION_CREDENTIAL_ID_B64,
        )
        self.assertEqual(result.new_sign_count, vectors.AUTHENTICATION_NEW_SIGN_COUNT)


@override_settings(
    CORS_ORIGIN_WHITELIST=["https://rmm.example.com"],
)
class TestWebAuthnViews(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.setup_client()
        self.bob = User(username="bob")
        self.bob.set_password("hunter2")
        self.bob.totp_key = "AB5RI6YPFTZAS52G"
        self.bob.save()
        self.cred = WebAuthnCredential.objects.create(
            user=self.bob,
            credential_id=wa.bytes_to_base64url(b"test-cred-id"),
            public_key=b"\x01\x02",
            sign_count=0,
            nickname="Test Key",
        )

    def test_check_creds_returns_passkey_flag(self):
        url = "/v2/checkcreds/"
        data = {"username": "bob", "password": "hunter2"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["totp"])
        self.assertTrue(r.data["passkey"])

    def test_check_creds_no_passkey_flag_without_credentials(self):
        self.cred.delete()
        url = "/v2/checkcreds/"
        data = {"username": "bob", "password": "hunter2"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["totp"])
        self.assertFalse(r.data["passkey"])

    @patch("pyotp.TOTP.verify")
    def test_totp_login_fallback_still_works(self, mock_verify):
        mock_verify.return_value = True
        url = "/v2/login/"
        data = {"username": "bob", "password": "hunter2", "twofactor": "123456"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("token", r.data)
        self.assertIn("expiry", r.data)

    def test_webauthn_login_begin_after_checkcreds(self):
        self.client.post(
            "/v2/checkcreds/",
            {"username": "bob", "password": "hunter2"},
            format="json",
        )
        r = self.client.post("/accounts/webauthn/login/begin/", {}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("challenge", r.data)
        self.assertIn("rpId", r.data)
        self.assertIn("hints", r.data)
        self.assertIn("allowCredentials", r.data)

    def test_webauthn_register_begin_authenticated(self):
        self.authenticate()
        r = self.client.post(
            "/accounts/webauthn/register/begin/?attachment=cross-platform",
            {},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("challenge", r.data)
        self.assertIn("rp", r.data)
        self.assertIn("pubKeyCredParams", r.data)
        self.assertEqual(r.data["hints"], ["hybrid"])
        self.assertEqual(
            r.data["authenticatorSelection"]["userVerification"], "preferred"
        )

    def test_passkey_list_rename_delete(self):
        self.authenticate()
        john_cred = WebAuthnCredential.objects.create(
            user=self.john,
            credential_id=wa.bytes_to_base64url(b"john-passkey"),
            public_key=b"\x05\x06",
            sign_count=0,
            nickname="John Key",
        )
        r = self.client.get("/accounts/passkeys/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)

        r = self.client.post(
            f"/accounts/passkeys/{john_cred.id}/rename/",
            {"nickname": "Renamed"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        john_cred.refresh_from_db()
        self.assertEqual(john_cred.nickname, "Renamed")

        r = self.client.post(
            f"/accounts/passkeys/{john_cred.id}/delete/",
            {},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(WebAuthnCredential.objects.filter(pk=john_cred.id).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                username=self.john.username,
                message__contains="deleted passkey",
            ).exists()
        )

    def test_admin_passkey_list_and_reset(self):
        self.authenticate()
        john_cred = WebAuthnCredential.objects.create(
            user=self.john,
            credential_id=wa.bytes_to_base64url(b"john-admin-passkey"),
            public_key=b"\x05\x06",
            sign_count=0,
            nickname="Admin Visible",
            last_used_at=djangotime.now(),
        )

        r = self.client.get(f"/accounts/users/{self.john.id}/passkeys/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]["id"], john_cred.id)
        self.assertEqual(r.data[0]["nickname"], "Admin Visible")
        self.assertIn("last_used_at", r.data[0])

        r = self.client.delete(f"/accounts/users/{self.john.id}/passkeys/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["deleted"], 1)
        self.assertFalse(WebAuthnCredential.objects.filter(pk=john_cred.id).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                username=self.john.username,
                message__contains="reset 1 passkey(s) for john",
            ).exists()
        )

    def test_delete_all_passkeys_does_not_block_totp_login(self):
        self.cred.delete()
        self.assertFalse(WebAuthnCredential.objects.filter(user=self.bob).exists())
        with patch("pyotp.TOTP.verify", return_value=True):
            r = self.client.post(
                "/v2/login/",
                {"username": "bob", "password": "hunter2", "twofactor": "123456"},
                format="json",
            )
        self.assertEqual(r.status_code, 200)
        self.assertIn("token", r.data)

    def test_mobile_login_begin_returns_challenge_id(self):
        r = self.client.post(
            "/accounts/webauthn/mobile/login/begin/",
            {"username": "bob", "device_id": "iphone-test"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("challenge", r.data)
        self.assertIn("challenge_id", r.data)
        self.assertIn("expires_at", r.data)
        self.assertEqual(r.data["userVerification"], "required")
        challenge = WebAuthnChallenge.objects.get(pk=r.data["challenge_id"])
        self.assertEqual(challenge.purpose, "login")
        self.assertEqual(challenge.device_id, "iphone-test")

    def test_mobile_login_begin_rejects_blocked_user(self):
        self.bob.block_dashboard_login = True
        self.bob.save(update_fields=["block_dashboard_login"])
        r = self.client.post(
            "/accounts/webauthn/mobile/login/begin/",
            {"username": "bob", "device_id": "iphone-test"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_mobile_challenge_consumed_on_replay(self):
        challenge = WebAuthnChallenge.objects.create(
            challenge="test-challenge-b64",
            purpose="login",
            user=self.bob,
            expires_at=djangotime.now() + timedelta(minutes=5),
            consumed_at=djangotime.now(),
        )
        r = self.client.post(
            "/accounts/webauthn/mobile/login/complete/",
            {
                "challenge_id": challenge.id,
                "credential": {"id": wa.bytes_to_base64url(b"test-cred-id")},
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_mobile_complete_rejects_malformed_challenge_id(self):
        r = self.client.post(
            "/accounts/webauthn/mobile/login/complete/",
            {
                "challenge_id": "not-an-int",
                "credential": {"id": wa.bytes_to_base64url(b"test-cred-id")},
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_mobile_bound_challenge_requires_device_id_on_complete(self):
        challenge = WebAuthnChallenge.objects.create(
            challenge="test-challenge-b64",
            purpose="login",
            user=self.bob,
            device_id="iphone-test",
            expires_at=djangotime.now() + timedelta(minutes=5),
        )
        r = self.client.post(
            "/accounts/webauthn/mobile/login/complete/",
            {
                "challenge_id": challenge.id,
                "credential": {"id": wa.bytes_to_base64url(b"test-cred-id")},
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_mobile_login_failed_verification_consumes_challenge(self):
        WebAuthnCredential.objects.create(
            user=self.bob,
            credential_id=vectors.AUTHENTICATION_CREDENTIAL_ID_B64,
            public_key=vectors.AUTHENTICATION_PUBLIC_KEY,
            sign_count=vectors.AUTHENTICATION_SIGN_COUNT,
        )
        challenge = WebAuthnChallenge.objects.create(
            challenge=vectors.AUTHENTICATION_CHALLENGE_B64,
            purpose="login",
            user=self.bob,
            device_id="iphone-test",
            expires_at=djangotime.now() + timedelta(minutes=5),
        )
        r = self.client.post(
            "/accounts/webauthn/mobile/login/complete/",
            {
                "challenge_id": challenge.id,
                "device_id": "iphone-test",
                "credential": json.loads(vectors.AUTHENTICATION_CREDENTIAL_JSON),
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        challenge.refresh_from_db()
        self.assertIsNotNone(challenge.consumed_at)

    def test_webauthn_reauth_begin_requires_passkey(self):
        self.authenticate()
        WebAuthnCredential.objects.create(
            user=self.john,
            credential_id=wa.bytes_to_base64url(b"john-cred"),
            public_key=b"\x03\x04",
            sign_count=0,
        )
        r = self.client.post("/accounts/webauthn/reauth/begin/", {}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("challenge", r.data)
        self.assertIn("hints", r.data)
        self.assertEqual(r.data["userVerification"], "required")

    def test_mobile_reauth_bound_challenge_requires_device_id(self):
        self.authenticate()
        WebAuthnCredential.objects.create(
            user=self.john,
            credential_id=wa.bytes_to_base64url(b"john-reauth-cred"),
            public_key=b"\x03\x04",
            sign_count=0,
        )
        challenge = WebAuthnChallenge.objects.create(
            challenge="test-challenge-b64",
            purpose="reauth",
            user=self.john,
            device_id="iphone-test",
            expires_at=djangotime.now() + timedelta(minutes=5),
        )
        r = self.client.post(
            "/accounts/webauthn/mobile/reauth/complete/",
            {
                "challenge_id": challenge.id,
                "credential": {"id": wa.bytes_to_base64url(b"john-reauth-cred")},
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_check_creds_requires_2fa_when_passkeys_without_totp(self):
        self.bob.totp_key = ""
        self.bob.save()
        r = self.client.post(
            "/v2/checkcreds/",
            {"username": "bob", "password": "hunter2"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["totp"])
        self.assertTrue(r.data["passkey"])
        self.assertNotIn("token", r.data)

    def test_mobile_login_begin_rejects_unknown_user(self):
        r = self.client.post(
            "/accounts/webauthn/mobile/login/begin/",
            {"username": "nobody", "device_id": "iphone-test"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_mobile_login_complete_rejects_orphan_challenge(self):
        challenge = WebAuthnChallenge.objects.create(
            challenge=vectors.AUTHENTICATION_CHALLENGE_B64,
            purpose="login",
            user=None,
            expires_at=djangotime.now() + timedelta(minutes=5),
        )
        r = self.client.post(
            "/accounts/webauthn/mobile/login/complete/",
            {
                "challenge_id": challenge.id,
                "credential": json.loads(vectors.AUTHENTICATION_CREDENTIAL_JSON),
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)


@override_settings(**LOCALHOST_SETTINGS)
class TestWebAuthnCompletePaths(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.setup_client()
        self.authenticate()
        self.john.totp_key = "AB5RI6YPFTZAS52G"
        self.john.save()

    def test_register_complete_persists_credential(self):
        session = self.client.session
        session[_WEBAUTHN_REGISTER_CHALLENGE] = _session_challenge(
            vectors.REGISTRATION_CHALLENGE_B64
        )
        session.save()
        r = self.client.post(
            "/accounts/webauthn/register/complete/",
            {
                "credential": json.loads(vectors.REGISTRATION_CREDENTIAL_JSON),
                "nickname": " Work Laptop ",
                "transports": ["usb", "usb", "internal", "invalid"],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["ok"])
        cred = WebAuthnCredential.objects.get(
            credential_id=vectors.REGISTRATION_CREDENTIAL_ID_B64
        )
        self.assertEqual(cred.user_id, self.john.id)
        self.assertEqual(cred.nickname, "Work Laptop")
        self.assertEqual(cred.transports, "usb,internal")
        self.assertTrue(
            AuditLog.objects.filter(
                username="john", action=AuditActionType.ADD
            ).exists()
        )

    def test_login_complete_issues_token_and_updates_sign_count(self):
        cred = WebAuthnCredential.objects.create(
            user=self.john,
            credential_id=vectors.AUTHENTICATION_CREDENTIAL_ID_B64,
            public_key=vectors.AUTHENTICATION_PUBLIC_KEY,
            sign_count=vectors.AUTHENTICATION_SIGN_COUNT,
        )
        session = self.client.session
        session[_PRE_2FA_USER_ID] = self.john.id
        session[_WEBAUTHN_LOGIN_CHALLENGE] = _session_challenge(
            vectors.AUTHENTICATION_CHALLENGE_B64
        )
        session.save()
        r = self.client.post(
            "/accounts/webauthn/login/complete/",
            {"credential": json.loads(vectors.AUTHENTICATION_CREDENTIAL_JSON)},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("token", r.data)
        cred.refresh_from_db()
        self.assertEqual(cred.sign_count, vectors.AUTHENTICATION_NEW_SIGN_COUNT)

    @patch("accounts.webauthn_views.wa.verify_authentication")
    def test_reauth_complete_updates_sign_count_and_audits(self, mock_verify):
        mock_verify.return_value = SimpleNamespace(new_sign_count=99)
        cred = WebAuthnCredential.objects.create(
            user=self.john,
            credential_id=vectors.AUTHENTICATION_CREDENTIAL_ID_B64,
            public_key=vectors.AUTHENTICATION_PUBLIC_KEY,
            sign_count=vectors.AUTHENTICATION_SIGN_COUNT,
        )
        session = self.client.session
        session[_WEBAUTHN_REAUTH_CHALLENGE] = _session_challenge(
            vectors.AUTHENTICATION_CHALLENGE_B64
        )
        session.save()
        r = self.client.post(
            "/accounts/webauthn/reauth/complete/",
            {"credential": json.loads(vectors.AUTHENTICATION_CREDENTIAL_JSON)},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["ok"])
        cred.refresh_from_db()
        self.assertEqual(cred.sign_count, 99)
        self.assertTrue(mock_verify.call_args.kwargs["require_user_verification"])
        self.assertTrue(
            AuditLog.objects.filter(
                username="john",
                action=AuditActionType.LOGIN,
                message__contains="step-up",
            ).exists()
        )

    def test_login_complete_rejects_expired_session_challenge(self):
        session = self.client.session
        session[_PRE_2FA_USER_ID] = self.john.id
        session[_WEBAUTHN_LOGIN_CHALLENGE] = _session_challenge(
            vectors.AUTHENTICATION_CHALLENGE_B64, minutes=-1
        )
        session.save()
        r = self.client.post(
            "/accounts/webauthn/login/complete/",
            {"credential": json.loads(vectors.AUTHENTICATION_CREDENTIAL_JSON)},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertNotIn(_WEBAUTHN_LOGIN_CHALLENGE, self.client.session)


@override_settings(
    CORS_ORIGIN_WHITELIST=["https://rmm.example.com"],
)
class TestWebAuthnEndpointContracts(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.setup_client()
        self.bob, _ = User.objects.get_or_create(username="contract_passkey_user")
        self.bob.set_password("contractpass123")
        self.bob.totp_key = "AB5RI6YPFTZAS52G"
        self.bob.save()
        WebAuthnCredential.objects.filter(user=self.bob).delete()
        WebAuthnCredential.objects.create(
            user=self.bob,
            credential_id=wa.bytes_to_base64url(b"contract-cred"),
            public_key=b"\xaa\xbb",
            sign_count=0,
        )

    def test_login_and_registration_begin_contract(self):
        r = self.client.post(
            "/v2/checkcreds/",
            {"username": "contract_passkey_user", "password": "contractpass123"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["passkey"])

        self.client.post(
            "/v2/checkcreds/",
            {"username": "contract_passkey_user", "password": "contractpass123"},
            format="json",
        )
        r = self.client.post("/accounts/webauthn/login/begin/", {}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("challenge", r.data)
        self.assertIn("rpId", r.data)

        self.authenticate()
        r = self.client.post(
            "/accounts/webauthn/register/begin/?attachment=cross-platform",
            {},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("challenge", r.data)
        self.assertIn("rp", r.data)
        self.assertIn("pubKeyCredParams", r.data)
        self.assertEqual(r.data["hints"], ["hybrid"])
