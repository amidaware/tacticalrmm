from django.urls import path

from . import views

urlpatterns = [
    path("", views.GetAddScripts.as_view()),
    path("<int:pk>/", views.GetUpdateDeleteScript.as_view()),
    path("snippets/", views.GetAddScriptSnippets.as_view()),
    path("snippets/<int:pk>/", views.GetUpdateDeleteScriptSnippet.as_view()),
    path("testscript/", views.TestScript.as_view()),
    path("download/<int:pk>/", views.download),
]
