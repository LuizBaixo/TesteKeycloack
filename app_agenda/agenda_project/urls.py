from django.contrib import admin
from django.urls import include, path
from agenda_project.oidc import GoogleOIDCAuthenticationRequestView
from core.views import create_appointment, delete_appointment, error_403, home

handler403 = error_403

urlpatterns = [
    path("admin/", admin.site.urls),
    path("oidc/google/login/", GoogleOIDCAuthenticationRequestView.as_view(), name="oidc_google_login"),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("appointments/new/", create_appointment, name="create_appointment"),
    path("appointments/<int:pk>/delete/", delete_appointment, name="delete_appointment"),
    path("", home, name="home"),
]
