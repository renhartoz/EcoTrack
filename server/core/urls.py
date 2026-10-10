from django.urls import path

from core.views import (
    HealthView,
    NasabahDetailView,
    NasabahListCreateView,
    WasteTypeListView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("nasabah/", NasabahListCreateView.as_view(), name="nasabah-list-create"),
    path("nasabah/<int:pk>/", NasabahDetailView.as_view(), name="nasabah-detail"),
    path("waste-types/", WasteTypeListView.as_view(), name="waste-type-list"),
]
