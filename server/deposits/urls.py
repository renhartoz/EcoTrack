from django.urls import path

from deposits.views import (
    DepositDetailView,
    DepositExportView,
    DepositListCreateView,
)

urlpatterns = [
    path("deposits/", DepositListCreateView.as_view(), name="deposit-list-create"),
    path("deposits/export/", DepositExportView.as_view(), name="deposit-export"),
    path("deposits/<int:pk>/", DepositDetailView.as_view(), name="deposit-detail"),
]
