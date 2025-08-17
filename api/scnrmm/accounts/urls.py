from django.urls import path

from . import views

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
    path("roles/", views.GetAddRoles.as_view()),
    path("roles/<int:pk>/", views.GetUpdateDeleteRole.as_view()),
    path("apikeys/", views.GetAddAPIKeys.as_view()),
    path("apikeys/<int:pk>/", views.GetUpdateDeleteAPIKey.as_view()),
    path("resetpw/", views.ResetPass.as_view()),
    path("reset2fa/", views.Reset2FA.as_view()),
]
