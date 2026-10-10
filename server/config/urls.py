from django.urls import include, path

urlpatterns = [
    path("api/auth/", include("accounts.urls")),
    path("api/", include("core.urls")),
    path("api/", include("ingestion.urls")),
    path("api/", include("deposits.urls")),
]

handler404 = "core.exceptions.handler404"
handler500 = "core.exceptions.handler500"
