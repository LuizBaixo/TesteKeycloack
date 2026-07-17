from django.contrib import admin
from django.urls import include, path
from tasks.views import create_task, delete_task, error_403, home, toggle_task
from todo_project.oidc import GoogleOIDCAuthenticationRequestView

handler403 = error_403

urlpatterns = [
    path("admin/", admin.site.urls),
    path("oidc/google/login/", GoogleOIDCAuthenticationRequestView.as_view(), name="oidc_google_login"),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("tasks/new/", create_task, name="create_task"),
    path("tasks/<int:pk>/toggle/", toggle_task, name="toggle_task"),
    path("tasks/<int:pk>/delete/", delete_task, name="delete_task"),
    path("", home, name="home"),
]
