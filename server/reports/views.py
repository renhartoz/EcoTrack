from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.mixins import BankScopedMixin
from core.permissions import IsBankOperator
from reports.serializers import (
    DashboardSummaryQuerySerializer,
    ImpactReportQuerySerializer,
)
from reports.services.dashboard import (
    get_current_month_range_jakarta,
    get_dashboard_summary,
)
from reports.services.impact import (
    get_current_month_jakarta,
    get_impact_report,
)


class DashboardSummaryView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def get(self, request):
        bank = self.get_bank()
        from_param = request.query_params.get("from")
        to_param = request.query_params.get("to")

        payload = {}
        if from_param is not None:
            payload["from_date"] = from_param
        if to_param is not None:
            payload["to_date"] = to_param

        serializer = DashboardSummaryQuerySerializer(data=payload)
        if not serializer.is_valid():
            return Response(
                {"error_code": "VALIDATION_ERROR", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated = serializer.validated_data
        from_date = validated.get("from_date")
        to_date = validated.get("to_date")

        default_from, default_to = get_current_month_range_jakarta()
        if from_date is None:
            from_date = default_from
        if to_date is None:
            to_date = default_to

        summary = get_dashboard_summary(bank, from_date, to_date)
        return Response(summary, status=status.HTTP_200_OK)


class ImpactReportView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def get(self, request):
        bank = self.get_bank()
        month_param = request.query_params.get("month")

        payload = {}
        if month_param is not None:
            payload["month"] = month_param

        serializer = ImpactReportQuerySerializer(data=payload)
        if not serializer.is_valid():
            return Response(
                {"error_code": "VALIDATION_ERROR", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parsed_month = serializer.validated_data.get("month")
        if parsed_month is None:
            year, month = get_current_month_jakarta()
        else:
            year, month = parsed_month

        report = get_impact_report(bank, year, month)
        return Response(report, status=status.HTTP_200_OK)
