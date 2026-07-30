import json
import logging
from datetime import timedelta

from django.contrib.auth import login
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.utils import timezone as djangotime
from knox.models import AuthToken
from knox.views import LoginView as KnoxLoginView
from python_ipware import IpWare
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import webauthn_service as wa
from accounts.models import User, WebAuthnChallenge, WebAuthnCredential
from accounts.permissions import AccountsPerms
from accounts.utils import can_dashboard_login, is_root_user
from logs.models import AuditLog
from tacticalrmm.helpers import notify_error
from tacticalrmm.throttles import LoginDayThrottle, LoginMinThrottle

logger = logging.getLogger("trmm")

PASSKEY_CHALLENGE_MINUTES = 5

_WEBAUTHN_LOGIN_CHALLENGE = "webauthn_login_challenge"
_WEBAUTHN_REGISTER_CHALLENGE = "webauthn_register_challenge"
_WEBAUTHN_REAUTH_CHALLENGE = "webauthn_reauth_challenge"
_PRE_2FA_USER_ID = "pre_2fa_user_id"

_ALLOWED_TRANSPORTS = {
    "ble",
    "cable",
    "hybrid",
    "internal",
    "nfc",
    "smart-card",
    "usb",
}


def _pre_2fa_user(request):
    uid = request.session.get(_PRE_2FA_USER_ID)
    if not uid:
        return None
    try:
        return User.objects.get(pk=uid)
    except User.DoesNotExist:
        return None


def _set_pre_2fa_user(request, user):
    request.session[_PRE_2FA_USER_ID] = user.id


def _clear_pre_2fa(request):
    request.session.pop(_PRE_2FA_USER_ID, None)
    request.session.pop(_WEBAUTHN_LOGIN_CHALLENGE, None)


def _clean_text(value, max_length, *, default=None):
    if not isinstance(value, str):
        return default
    value = value.strip()
    return value[:max_length] if value else default


def _clean_transports(transports):
    if not isinstance(transports, list):
        return None

    cleaned = []
    for transport in transports:
        transport = _clean_text(transport, 50)
        if transport in _ALLOWED_TRANSPORTS and transport not in cleaned:
            cleaned.append(transport)

    return ",".join(cleaned)[:255] or None


def _credential_from_request(request):
    cred_json = request.data.get("credential")
    return cred_json if isinstance(cred_json, dict) else None


def _credential_ids(user):
    return list(user.webauthn_credentials.values_list("credential_id", flat=True))


def _store_session_challenge(request, key, challenge):
    request.session[key] = {
        "challenge": challenge,
        "expires_at": (
            djangotime.now() + timedelta(minutes=PASSKEY_CHALLENGE_MINUTES)
        ).isoformat(),
    }


def _pop_session_challenge(request, key):
    request.session.pop(key, None)


def _load_session_challenge(request, key):
    payload = request.session.get(key)
    if not isinstance(payload, dict):
        _pop_session_challenge(request, key)
        return None

    challenge = payload.get("challenge")
    expires_at = parse_datetime(payload.get("expires_at") or "")
    if not isinstance(challenge, str) or not challenge or expires_at is None:
        _pop_session_challenge(request, key)
        return None

    if djangotime.is_naive(expires_at):
        expires_at = djangotime.make_aware(
            expires_at, djangotime.get_current_timezone()
        )

    if expires_at <= djangotime.now():
        _pop_session_challenge(request, key)
        return None

    return challenge


def _issue_knox_token(request, user):
    """Issue a Knox auth token after successful 2FA, mirroring LoginViewV2."""
    login(request, user)
    ipw = IpWare()
    client_ip, _ = ipw.get_client_ip(request.META)
    if client_ip:
        user.last_login_ip = str(client_ip)
        user.save(update_fields=["last_login_ip"])
    token_obj, token = AuthToken.objects.create(user)
    return {
        "expiry": token_obj.expiry,
        "token": token,
        "username": user.username,
        "name": None,
    }


def _challenge_payload(challenge):
    return {
        "challenge_id": challenge.id,
        "expires_at": challenge.expires_at.isoformat(),
    }


def _record_challenge(options, purpose, *, user=None, device_id=None):
    return WebAuthnChallenge.objects.create(
        challenge=wa.bytes_to_base64url(options.challenge),
        purpose=purpose,
        user=user,
        device_id=_clean_text(device_id, 128),
        expires_at=djangotime.now() + timedelta(minutes=PASSKEY_CHALLENGE_MINUTES),
    )


def _load_challenge(challenge_id, purpose, *, user=None):
    try:
        challenge_pk = int(challenge_id)
    except (TypeError, ValueError):
        return None, notify_error("challenge not found")

    try:
        challenge = WebAuthnChallenge.objects.get(pk=challenge_pk)
    except WebAuthnChallenge.DoesNotExist:
        return None, notify_error("challenge not found")
    if challenge.purpose != purpose:
        return None, notify_error("challenge not found")
    if user is not None and challenge.user_id != user.id:
        return None, notify_error("challenge not found")
    if challenge.consumed_at is not None:
        return None, notify_error("challenge already used")
    if challenge.expires_at <= djangotime.now():
        return None, notify_error("challenge expired")
    return challenge, None


def _consume_challenge(challenge):
    consumed_at = djangotime.now()
    updated = WebAuthnChallenge.objects.filter(
        pk=challenge.pk, consumed_at__isnull=True
    ).update(consumed_at=consumed_at)
    if updated:
        challenge.consumed_at = consumed_at
    return bool(updated)


def _create_credential(user, *, credential_id, public_key, sign_count, **fields):
    """Persist a passkey; map unique-credential races to a client error."""
    try:
        return WebAuthnCredential.objects.create(
            user=user,
            credential_id=credential_id,
            public_key=public_key,
            sign_count=sign_count,
            **fields,
        )
    except IntegrityError:
        return None


def _challenge_device_id(challenge, data):
    payload_device_id = _clean_text(data.get("device_id"), 128)
    if challenge.device_id:
        if payload_device_id != challenge.device_id:
            return None, notify_error("challenge not found")
        return challenge.device_id, None
    return payload_device_id, None


def _passkey_payload(credential):
    return {
        "id": credential.id,
        "nickname": credential.nickname,
        "transports": (
            credential.transports.split(",") if credential.transports else []
        ),
        "created_at": credential.created_time,
        "last_used_at": credential.last_used_at,
        "device_id": credential.device_id,
    }


class WebAuthnLoginBegin(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [LoginMinThrottle, LoginDayThrottle]

    def post(self, request):
        user = _pre_2fa_user(request)
        if not user or not user.webauthn_credentials.exists():
            return notify_error("session expired")
        opts = wa.authentication_options(_credential_ids(user))
        _store_session_challenge(
            request, _WEBAUTHN_LOGIN_CHALLENGE, wa.bytes_to_base64url(opts.challenge)
        )
        return Response(json.loads(wa.authentication_options_to_json(opts)))


class WebAuthnLoginComplete(KnoxLoginView):
    permission_classes = (AllowAny,)
    throttle_classes = [LoginMinThrottle, LoginDayThrottle]

    def post(self, request):
        user = _pre_2fa_user(request)
        challenge = _load_session_challenge(request, _WEBAUTHN_LOGIN_CHALLENGE)
        if not user or not challenge:
            return notify_error("session expired")
        cred_json = _credential_from_request(request)
        if cred_json is None:
            _pop_session_challenge(request, _WEBAUTHN_LOGIN_CHALLENGE)
            return notify_error("verification failed")
        cred = user.webauthn_credentials.filter(
            credential_id=cred_json.get("id")
        ).first()
        if cred is None:
            _pop_session_challenge(request, _WEBAUTHN_LOGIN_CHALLENGE)
            return notify_error("verification failed")
        try:
            result = wa.verify_authentication(
                json.dumps(cred_json), challenge, cred.public_key, cred.sign_count
            )
        except Exception as exc:
            _pop_session_challenge(request, _WEBAUTHN_LOGIN_CHALLENGE)
            logger.warning(
                "webauthn login verify failed user=%s: %s", user.username, exc
            )
            AuditLog.audit_user_failed_twofactor(
                user.username,
                debug_info={"ip": request._client_ip, "method": "passkey"},
            )
            return notify_error("verification failed")
        cred.sign_count = result.new_sign_count
        cred.last_used_at = djangotime.now()
        cred.save(update_fields=["sign_count", "last_used_at"])
        _clear_pre_2fa(request)
        AuditLog.audit_user_login_successful(
            user.username,
            debug_info={"ip": request._client_ip, "method": "passkey"},
        )
        return Response(_issue_knox_token(request, user))


class WebAuthnReauthBegin(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        if not user.webauthn_credentials.exists():
            return notify_error("no passkey enrolled")
        opts = wa.authentication_options(
            _credential_ids(user), require_user_verification=True
        )
        _store_session_challenge(
            request, _WEBAUTHN_REAUTH_CHALLENGE, wa.bytes_to_base64url(opts.challenge)
        )
        return Response(json.loads(wa.authentication_options_to_json(opts)))


class WebAuthnReauthComplete(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        challenge = _load_session_challenge(request, _WEBAUTHN_REAUTH_CHALLENGE)
        if not challenge:
            return notify_error("session expired")
        cred_json = _credential_from_request(request)
        if cred_json is None:
            _pop_session_challenge(request, _WEBAUTHN_REAUTH_CHALLENGE)
            return notify_error("verification failed")
        cred = user.webauthn_credentials.filter(
            credential_id=cred_json.get("id")
        ).first()
        if cred is None:
            _pop_session_challenge(request, _WEBAUTHN_REAUTH_CHALLENGE)
            return notify_error("verification failed")
        try:
            result = wa.verify_authentication(
                json.dumps(cred_json),
                challenge,
                cred.public_key,
                cred.sign_count,
                require_user_verification=True,
            )
        except Exception as exc:
            _pop_session_challenge(request, _WEBAUTHN_REAUTH_CHALLENGE)
            logger.warning(
                "webauthn reauth verify failed user=%s: %s", user.username, exc
            )
            AuditLog.audit_passkey_reauth_failed(
                user.username, debug_info={"ip": request._client_ip}
            )
            return notify_error("verification failed")
        cred.sign_count = result.new_sign_count
        cred.last_used_at = djangotime.now()
        cred.save(update_fields=["sign_count", "last_used_at"])
        _pop_session_challenge(request, _WEBAUTHN_REAUTH_CHALLENGE)
        request.session["webauthn_reauth_at"] = djangotime.now().isoformat()
        AuditLog.audit_passkey_reauth_successful(
            user.username, debug_info={"ip": request._client_ip}
        )
        return Response({"ok": True})


class WebAuthnRegisterBegin(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        attachment = request.query_params.get("attachment")
        if attachment not in ("platform", "cross-platform"):
            attachment = request.data.get("attachment")
        if attachment not in ("platform", "cross-platform"):
            attachment = None
        opts = wa.registration_options(
            request.user,
            _credential_ids(request.user),
            attachment=attachment,
        )
        _store_session_challenge(
            request, _WEBAUTHN_REGISTER_CHALLENGE, wa.bytes_to_base64url(opts.challenge)
        )
        return Response(json.loads(wa.options_to_json(opts)))


class WebAuthnRegisterComplete(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        challenge = _load_session_challenge(request, _WEBAUTHN_REGISTER_CHALLENGE)
        if not challenge:
            return notify_error("session expired")
        cred_json = _credential_from_request(request)
        if cred_json is None:
            _pop_session_challenge(request, _WEBAUTHN_REGISTER_CHALLENGE)
            return notify_error("verification failed")
        nickname = _clean_text(request.data.get("nickname"), 100)
        try:
            verified = wa.verify_registration(json.dumps(cred_json), challenge)
        except Exception as exc:
            _pop_session_challenge(request, _WEBAUTHN_REGISTER_CHALLENGE)
            logger.warning(
                "webauthn register verify failed user=%s: %s",
                request.user.username,
                exc,
            )
            AuditLog.audit_passkey_register_failed(
                request.user.username, debug_info={"ip": request._client_ip}
            )
            return notify_error("verification failed")
        cred_id = wa.bytes_to_base64url(verified.credential_id)
        cred = _create_credential(
            request.user,
            credential_id=cred_id,
            public_key=verified.credential_public_key,
            sign_count=verified.sign_count,
            transports=_clean_transports(request.data.get("transports")),
            nickname=nickname,
        )
        if cred is None:
            _pop_session_challenge(request, _WEBAUTHN_REGISTER_CHALLENGE)
            AuditLog.audit_passkey_register_failed(
                request.user.username, debug_info={"ip": request._client_ip}
            )
            return notify_error("passkey already registered")
        _pop_session_challenge(request, _WEBAUTHN_REGISTER_CHALLENGE)
        AuditLog.audit_passkey_registered(
            request.user.username,
            debug_info={"ip": request._client_ip, "credential_id": cred_id},
        )
        return Response({"ok": True, "id": cred.id, "nickname": cred.nickname})


class PasskeyList(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        creds = request.user.webauthn_credentials.all()
        return Response([_passkey_payload(cred) for cred in creds])


class PasskeyRename(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        cred = request.user.webauthn_credentials.filter(pk=pk).first()
        if cred is None:
            return notify_error("passkey not found")
        cred.nickname = _clean_text(request.data.get("nickname"), 100)
        cred.save(update_fields=["nickname"])
        return Response({"ok": True, "nickname": cred.nickname})


class PasskeyDelete(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        cred = request.user.webauthn_credentials.filter(pk=pk).first()
        if cred is None:
            return notify_error("passkey not found")
        nickname = cred.nickname or str(cred.id)
        cred.delete()
        AuditLog.audit_passkey_deleted(
            request.user.username,
            nickname,
            debug_info={"ip": request._client_ip, "credential_id": pk},
        )
        return Response({"ok": True})


class UserPasskeyListReset(APIView):
    permission_classes = [IsAuthenticated, AccountsPerms]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        creds = user.webauthn_credentials.all()
        return Response([_passkey_payload(cred) for cred in creds])

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if is_root_user(request=request, user=user):
            return notify_error("The root user cannot be modified from the UI")

        count = user.webauthn_credentials.count()
        user.webauthn_credentials.all().delete()
        AuditLog.audit_passkeys_reset(
            request.user.username,
            user.username,
            count,
            debug_info={"ip": request._client_ip, "target_user_id": user.id},
        )
        return Response({"ok": True, "deleted": count})


class MobilePasskeyLoginBegin(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [LoginMinThrottle, LoginDayThrottle]

    def post(self, request):
        username = _clean_text(request.data.get("username"), 150)
        device_id = _clean_text(request.data.get("device_id"), 128)
        if not username:
            return notify_error("Bad credentials")
        user = User.objects.filter(username=username).first()
        if (
            user is None
            or not can_dashboard_login(user)
            or not user.webauthn_credentials.exists()
        ):
            return notify_error("Bad credentials")
        opts = wa.authentication_options(
            _credential_ids(user), require_user_verification=True
        )
        challenge = _record_challenge(opts, "login", user=user, device_id=device_id)
        body = json.loads(wa.authentication_options_to_json(opts))
        body.update(_challenge_payload(challenge))
        return Response(body)


class MobilePasskeyLoginComplete(KnoxLoginView):
    permission_classes = (AllowAny,)
    throttle_classes = [LoginMinThrottle, LoginDayThrottle]

    def post(self, request):
        challenge, error = _load_challenge(request.data.get("challenge_id"), "login")
        if error:
            return error
        _device_id, error = _challenge_device_id(challenge, request.data)
        if error:
            return error
        cred_json = _credential_from_request(request)
        if cred_json is None:
            return notify_error("verification failed")
        if challenge.user_id is None:
            return notify_error("challenge not found")
        cred = (
            WebAuthnCredential.objects.select_related("user")
            .filter(credential_id=cred_json.get("id"))
            .first()
        )
        if cred is None or cred.user_id != challenge.user_id:
            return notify_error("verification failed")
        if not can_dashboard_login(cred.user):
            _consume_challenge(challenge)
            AuditLog.audit_user_failed_login(
                cred.user.username,
                debug_info={"ip": request._client_ip, "method": "passkey"},
            )
            return notify_error("Bad credentials")
        try:
            result = wa.verify_authentication(
                json.dumps(cred_json),
                challenge.challenge,
                cred.public_key,
                cred.sign_count,
                require_user_verification=True,
            )
        except Exception as exc:
            _consume_challenge(challenge)
            logger.warning(
                "webauthn mobile login verify failed user=%s: %s",
                cred.user.username,
                exc,
            )
            AuditLog.audit_user_failed_twofactor(
                cred.user.username,
                debug_info={"ip": request._client_ip, "method": "passkey"},
            )
            return notify_error("verification failed")
        if not _consume_challenge(challenge):
            return notify_error("challenge already used")
        cred.sign_count = result.new_sign_count
        cred.last_used_at = djangotime.now()
        cred.save(update_fields=["sign_count", "last_used_at"])
        AuditLog.audit_user_login_successful(
            cred.user.username,
            debug_info={"ip": request._client_ip, "method": "passkey"},
        )
        return Response(_issue_knox_token(request, cred.user))


class MobilePasskeyRegisterBegin(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        attachment = request.data.get("attachment")
        if attachment not in ("platform", "cross-platform"):
            attachment = None
        opts = wa.registration_options(
            request.user,
            _credential_ids(request.user),
            attachment=attachment,
        )
        challenge = _record_challenge(
            opts,
            "register",
            user=request.user,
            device_id=request.data.get("device_id"),
        )
        body = json.loads(wa.options_to_json(opts))
        body.update(_challenge_payload(challenge))
        return Response(body)


class MobilePasskeyRegisterComplete(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        challenge, error = _load_challenge(
            request.data.get("challenge_id"), "register", user=request.user
        )
        if error:
            return error
        device_id, error = _challenge_device_id(challenge, request.data)
        if error:
            return error
        cred_json = _credential_from_request(request)
        if cred_json is None:
            _consume_challenge(challenge)
            return notify_error("verification failed")
        try:
            verified = wa.verify_registration(
                json.dumps(cred_json), challenge.challenge
            )
        except Exception as exc:
            _consume_challenge(challenge)
            logger.warning(
                "webauthn mobile register verify failed user=%s: %s",
                request.user.username,
                exc,
            )
            AuditLog.audit_passkey_register_failed(
                request.user.username, debug_info={"ip": request._client_ip}
            )
            return notify_error("verification failed")
        if not _consume_challenge(challenge):
            return notify_error("challenge already used")
        cred_id = wa.bytes_to_base64url(verified.credential_id)
        cred = _create_credential(
            request.user,
            credential_id=cred_id,
            public_key=verified.credential_public_key,
            sign_count=verified.sign_count,
            transports=_clean_transports(request.data.get("transports")),
            nickname=_clean_text(request.data.get("nickname"), 100, default="Mobile"),
            device_id=(device_id or "")[:128] or None,
        )
        if cred is None:
            AuditLog.audit_passkey_register_failed(
                request.user.username, debug_info={"ip": request._client_ip}
            )
            return notify_error("passkey already registered")
        AuditLog.audit_passkey_registered(
            request.user.username,
            debug_info={"ip": request._client_ip, "credential_id": cred_id},
        )
        return Response({"ok": True, "id": cred.id, "nickname": cred.nickname})


class MobilePasskeyReauthBegin(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if not request.user.webauthn_credentials.exists():
            return notify_error("no passkey enrolled")
        opts = wa.authentication_options(
            _credential_ids(request.user), require_user_verification=True
        )
        challenge = _record_challenge(
            opts,
            "reauth",
            user=request.user,
            device_id=request.data.get("device_id"),
        )
        body = json.loads(wa.options_to_json(opts))
        body.update(_challenge_payload(challenge))
        return Response(body)


class MobilePasskeyReauthComplete(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        challenge, error = _load_challenge(
            request.data.get("challenge_id"), "reauth", user=request.user
        )
        if error:
            return error
        _device_id, error = _challenge_device_id(challenge, request.data)
        if error:
            return error
        cred_json = _credential_from_request(request)
        if cred_json is None:
            _consume_challenge(challenge)
            return notify_error("verification failed")
        cred = request.user.webauthn_credentials.filter(
            credential_id=cred_json.get("id")
        ).first()
        if cred is None:
            return notify_error("verification failed")
        try:
            result = wa.verify_authentication(
                json.dumps(cred_json),
                challenge.challenge,
                cred.public_key,
                cred.sign_count,
                require_user_verification=True,
            )
        except Exception as exc:
            _consume_challenge(challenge)
            logger.warning(
                "webauthn mobile reauth verify failed user=%s: %s",
                request.user.username,
                exc,
            )
            AuditLog.audit_passkey_reauth_failed(
                request.user.username, debug_info={"ip": request._client_ip}
            )
            return notify_error("verification failed")
        if not _consume_challenge(challenge):
            return notify_error("challenge already used")
        cred.sign_count = result.new_sign_count
        cred.last_used_at = djangotime.now()
        cred.save(update_fields=["sign_count", "last_used_at"])
        AuditLog.audit_passkey_reauth_successful(
            request.user.username, debug_info={"ip": request._client_ip}
        )
        return Response({"ok": True})
