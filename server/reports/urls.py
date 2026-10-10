from django.urls import path

from reports.views import DashboardSummaryView, ImpactReportView

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("reports/impact/", ImpactReportView.as_view(), name="reports-impact"),
]
