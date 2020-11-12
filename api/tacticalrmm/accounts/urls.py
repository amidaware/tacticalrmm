from django.urls import path
from . import views

urlpatterns = [
    path("users/", views.GetAddUsers.as_view()),
    path("<int:pk>/users/", views.GetUpdateDeleteUser.as_view()),
    path("users/reset/", views.UserActions.as_view()),
    path("users/reset_totp/", views.UserActions.as_view()),
    path("users/setup_totp/", views.TOTPSetup.as_view()),
    path("users/ui/", views.UserUI.as_view()),
]
