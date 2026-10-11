from django.urls import path

from ingestion.views import (
    ExtractedRowConfirmView,
    ExtractedRowDetailView,
    ExtractedRowRejectView,
    UploadConfirmAllView,
    UploadDetailView,
    UploadImageView,
    UploadListCreateView,
    UploadRetryView,
    UploadTextView,
)

urlpatterns = [
    path("uploads/", UploadListCreateView.as_view(), name="upload-list-create"),
    path("uploads/text/", UploadTextView.as_view(), name="upload-text"),
    path("uploads/<uuid:pk>/", UploadDetailView.as_view(), name="upload-detail"),
    path("uploads/<uuid:pk>/image/", UploadImageView.as_view(), name="upload-image"),
    path("uploads/<uuid:pk>/retry/", UploadRetryView.as_view(), name="upload-retry"),
    path(
        "uploads/<uuid:pk>/confirm-all/",
        UploadConfirmAllView.as_view(),
        name="upload-confirm-all",
    ),
    path("rows/<int:pk>/", ExtractedRowDetailView.as_view(), name="row-detail"),
    path("rows/<int:pk>/confirm/", ExtractedRowConfirmView.as_view(), name="row-confirm"),
    path("rows/<int:pk>/reject/", ExtractedRowRejectView.as_view(), name="row-reject"),
]
