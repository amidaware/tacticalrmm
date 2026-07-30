from django.urls import path

from . import views
from . import webauthn_views as wa_views

urlpatterns = [
    path("users/", views.GetAddUsers.as_view()),
    path("<int:pk>/users/", views.GetUpdateDeleteUser.as_view()),
    path("sessions/<str:pk>/", views.DeleteActiveLoginSession.as_view()),
    path(
        "users/<int:pk>/sessions/", views.GetDeleteActiveLoginSessionsPerUser.as_view()
    ),
    path("users/reset/", views.UserActions.as_view()),
    path("users/reset_totp/", views.UserActions.as_view()),
    path("users/setup_totp/", views.TOTPSetup.as_view()),
    path("users/ui/", views.UserUI.as_view()),
    path("users/<int:pk>/passkeys/", wa_views.UserPasskeyListReset.as_view()),
    path("roles/", views.GetAddRoles.as_view()),
    path("roles/<int:pk>/", views.GetUpdateDeleteRole.as_view()),
    path("apikeys/", views.GetAddAPIKeys.as_view()),
    path("apikeys/<int:pk>/", views.GetUpdateDeleteAPIKey.as_view()),
    path("resetpw/", views.ResetPass.as_view()),
    path("reset2fa/", views.Reset2FA.as_view()),
    path("webauthn/login/begin/", wa_views.WebAuthnLoginBegin.as_view()),
    path("webauthn/login/complete/", wa_views.WebAuthnLoginComplete.as_view()),
    path("webauthn/reauth/begin/", wa_views.WebAuthnReauthBegin.as_view()),
    path("webauthn/reauth/complete/", wa_views.WebAuthnReauthComplete.as_view()),
    path("webauthn/register/begin/", wa_views.WebAuthnRegisterBegin.as_view()),
    path("webauthn/register/complete/", wa_views.WebAuthnRegisterComplete.as_view()),
    path("passkeys/", wa_views.PasskeyList.as_view()),
    path("passkeys/<int:pk>/rename/", wa_views.PasskeyRename.as_view()),
    path("passkeys/<int:pk>/delete/", wa_views.PasskeyDelete.as_view()),
    path(
        "webauthn/mobile/login/begin/",
        wa_views.MobilePasskeyLoginBegin.as_view(),
    ),
    path(
        "webauthn/mobile/login/complete/",
        wa_views.MobilePasskeyLoginComplete.as_view(),
    ),
    path(
        "webauthn/mobile/register/begin/",
        wa_views.MobilePasskeyRegisterBegin.as_view(),
    ),
    path(
        "webauthn/mobile/register/complete/",
        wa_views.MobilePasskeyRegisterComplete.as_view(),
    ),
    path(
        "webauthn/mobile/reauth/begin/",
        wa_views.MobilePasskeyReauthBegin.as_view(),
    ),
    path(
        "webauthn/mobile/reauth/complete/",
        wa_views.MobilePasskeyReauthComplete.as_view(),
    ),
]
