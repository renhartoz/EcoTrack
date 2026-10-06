from django.urls import path

from ingestion.views import (
    UploadDetailView,
    UploadImageView,
    UploadListCreateView,
    UploadRetryView,
    UploadTextView,
)

urlpatterns = [
    path("uploads/", UploadListCreateView.as_view(), name="upload-list-create"),
    path("uploads/text/", UploadTextView.as_view(), name="upload-text"),
    path("uploads/<int:pk>/", UploadDetailView.as_view(), name="upload-detail"),
    path("uploads/<int:pk>/image/", UploadImageView.as_view(), name="upload-image"),
    path("uploads/<int:pk>/retry/", UploadRetryView.as_view(), name="upload-retry"),
]
