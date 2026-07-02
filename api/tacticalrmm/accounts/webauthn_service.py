"""WebAuthn/passkey helpers."""

import json
from urllib.parse import urlparse

from django.conf import settings
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialHint,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

__all__ = [
    "RP_NAME",
    "authentication_options",
    "authentication_options_to_json",
    "base64url_to_bytes",
    "bytes_to_base64url",
    "options_to_json",
    "registration_options",
    "rp_id",
    "rp_origin",
    "verify_authentication",
    "verify_registration",
]

_SECOND_FACTOR_UV = UserVerificationRequirement.PREFERRED
_REAUTH_UV = UserVerificationRequirement.REQUIRED
_LOCAL_FIRST_AUTH_HINTS = [
    PublicKeyCredentialHint.CLIENT_DEVICE.value,
    PublicKeyCredentialHint.HYBRID.value,
    PublicKeyCredentialHint.SECURITY_KEY.value,
]


def _frontend_origin() -> str:
    origins = getattr(settings, "CORS_ORIGIN_WHITELIST", None) or []
    if origins:
        return origins[0].strip().rstrip("/")
    return "https://localhost"


def rp_origin() -> str:
    return _frontend_origin()


def rp_id() -> str:
    return urlparse(rp_origin()).hostname or "localhost"


RP_NAME = getattr(settings, "WEBAUTHN_RP_NAME", "Tactical RMM")


def registration_options(user, existing_cred_ids, attachment=None):
    selection = AuthenticatorSelectionCriteria(
        resident_key=ResidentKeyRequirement.REQUIRED,
        user_verification=_SECOND_FACTOR_UV,
    )
    if attachment == "platform":
        selection.authenticator_attachment = AuthenticatorAttachment.PLATFORM
        hints = [PublicKeyCredentialHint.CLIENT_DEVICE]
    elif attachment == "cross-platform":
        selection.authenticator_attachment = AuthenticatorAttachment.CROSS_PLATFORM
        hints = [PublicKeyCredentialHint.HYBRID]
    else:
        hints = [
            PublicKeyCredentialHint.CLIENT_DEVICE,
            PublicKeyCredentialHint.HYBRID,
            PublicKeyCredentialHint.SECURITY_KEY,
        ]
    return generate_registration_options(
        rp_id=rp_id(),
        rp_name=RP_NAME,
        user_id=str(user.id).encode("utf-8"),
        user_name=user.username,
        user_display_name=user.username,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=selection,
        hints=hints,
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(cid))
            for cid in existing_cred_ids
        ],
        timeout=300000,
    )


def verify_registration(response, expected_challenge_b64):
    return verify_registration_response(
        credential=response,
        expected_challenge=base64url_to_bytes(expected_challenge_b64),
        expected_origin=rp_origin(),
        expected_rp_id=rp_id(),
    )


def authentication_options(allow_cred_ids, *, require_user_verification=False):
    return generate_authentication_options(
        rp_id=rp_id(),
        user_verification=(
            _REAUTH_UV if require_user_verification else _SECOND_FACTOR_UV
        ),
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(cid))
            for cid in allow_cred_ids
        ]
        or None,
        timeout=300000,
    )


def authentication_options_to_json(options) -> str:
    body = json.loads(options_to_json(options))
    body["hints"] = list(_LOCAL_FIRST_AUTH_HINTS)
    return json.dumps(body)


def verify_authentication(
    response,
    expected_challenge_b64,
    public_key_bytes,
    sign_count,
    *,
    require_user_verification=False,
):
    return verify_authentication_response(
        credential=response,
        expected_challenge=base64url_to_bytes(expected_challenge_b64),
        expected_origin=rp_origin(),
        expected_rp_id=rp_id(),
        credential_public_key=public_key_bytes,
        credential_current_sign_count=sign_count,
        require_user_verification=require_user_verification,
    )
