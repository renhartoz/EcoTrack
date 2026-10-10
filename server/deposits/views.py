import csv

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from core.mixins import BankScopedMixin
from core.permissions import IsBankOperator
from deposits.models import AuditLog, Deposit
from deposits.serializers import (
    DepositCreateSerializer,
    DepositSerializer,
    DepositUpdateSerializer,
)


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def apply_deposit_filters(queryset, params):
    from_date = params.get("from")
    to_date = params.get("to")
    nasabah_id = params.get("nasabah")
    waste_type_id = params.get("waste_type")
    source = params.get("source")

    if from_date:
        queryset = queryset.filter(deposit_date__gte=from_date)
    if to_date:
        queryset = queryset.filter(deposit_date__lte=to_date)
    if nasabah_id:
        queryset = queryset.filter(nasabah_id=nasabah_id)
    if waste_type_id:
        queryset = queryset.filter(waste_type_id=waste_type_id)
    if source:
        queryset = queryset.filter(source=source)

    return queryset


class DepositListCreateView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def get(self, request):
        bank = self.get_bank()
        queryset = (
            Deposit.objects.filter(bank_sampah=bank, deleted_at__isnull=True)
            .select_related("nasabah", "waste_type", "upload")
            .order_by("-deposit_date", "-created_at")
        )
        queryset = apply_deposit_filters(queryset, request.query_params)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = DepositSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        bank = self.get_bank()
        serializer = DepositCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            deposit = Deposit.objects.create(
                bank_sampah=bank,
                nasabah=data["nasabah"],
                waste_type=data["waste_type"],
                weight_kg=data["weight_kg"],
                deposit_date=data["deposit_date"],
                source="manual",
                created_by=request.user,
            )
            AuditLog.objects.create(
                bank_sampah=bank,
                actor=request.user,
                actor_label=request.user.username,
                action="create",
                entity_type="deposit",
                entity_id=deposit.id,
                before={},
                after={
                    "nasabah_id": deposit.nasabah_id,
                    "waste_type_id": deposit.waste_type_id,
                    "weight_kg": str(deposit.weight_kg),
                    "deposit_date": str(deposit.deposit_date),
                    "source": deposit.source,
                },
            )

        return Response(DepositSerializer(deposit).data, status=status.HTTP_201_CREATED)


class DepositDetailView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def patch(self, request, pk):
        bank = self.get_bank()
        with transaction.atomic():
            deposit = self.get_scoped_object_or_404(
                Deposit.objects.select_for_update().filter(deleted_at__isnull=True),
                pk=pk,
            )
            serializer = DepositUpdateSerializer(
                data=request.data,
                partial=True,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            before_state = {
                "nasabah_id": deposit.nasabah_id,
                "waste_type_id": deposit.waste_type_id,
                "weight_kg": str(deposit.weight_kg),
                "deposit_date": str(deposit.deposit_date),
            }

            if "nasabah" in data:
                deposit.nasabah = data["nasabah"]
            if "waste_type" in data:
                deposit.waste_type = data["waste_type"]
            if "weight_kg" in data:
                deposit.weight_kg = data["weight_kg"]
            if "deposit_date" in data:
                deposit.deposit_date = data["deposit_date"]

            deposit.save()

            after_state = {
                "nasabah_id": deposit.nasabah_id,
                "waste_type_id": deposit.waste_type_id,
                "weight_kg": str(deposit.weight_kg),
                "deposit_date": str(deposit.deposit_date),
            }

            AuditLog.objects.create(
                bank_sampah=bank,
                actor=request.user,
                actor_label=request.user.username,
                action="update",
                entity_type="deposit",
                entity_id=deposit.id,
                before=before_state,
                after=after_state,
            )

        return Response(DepositSerializer(deposit).data)

    def delete(self, request, pk):
        bank = self.get_bank()
        with transaction.atomic():
            deposit = self.get_scoped_object_or_404(Deposit.objects.select_for_update(), pk=pk)
            if deposit.deleted_at is not None:
                return Response(
                    {"error": {"code": "ROW_NOT_PENDING", "message": "Deposit already deleted."}},
                    status=status.HTTP_409_CONFLICT,
                )

            now = timezone.now()
            deposit.deleted_at = now
            deposit.save(update_fields=["deleted_at"])

            AuditLog.objects.create(
                bank_sampah=bank,
                actor=request.user,
                actor_label=request.user.username,
                action="delete",
                entity_type="deposit",
                entity_id=deposit.id,
                before={"deleted_at": None},
                after={"deleted_at": now.isoformat()},
            )

            row = getattr(deposit, "extracted_row", None)
            if row is not None:
                from ingestion.models import ExtractedRow

                locked_row = ExtractedRow.objects.select_for_update().get(id=row.id)
                locked_row.status = "reverted"
                locked_row.save(update_fields=["status"])
                AuditLog.objects.create(
                    bank_sampah=bank,
                    actor=request.user,
                    actor_label=request.user.username,
                    action="revert",
                    entity_type="extracted_row",
                    entity_id=locked_row.id,
                    before={"status": "saved"},
                    after={"status": "reverted"},
                )

        return Response({"status": "ok", "deleted_at": now.isoformat()})


class DepositExportView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def get(self, request):
        bank = self.get_bank()
        queryset = (
            Deposit.objects.filter(bank_sampah=bank, deleted_at__isnull=True)
            .select_related("nasabah", "waste_type")
            .order_by("-deposit_date", "-created_at")
        )
        queryset = apply_deposit_filters(queryset, request.query_params)

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="deposits_export.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "id",
                "nasabah",
                "waste_type",
                "weight_kg",
                "deposit_date",
                "source",
                "created_at",
            ]
        )

        for dep in queryset:
            writer.writerow(
                [
                    dep.id,
                    dep.nasabah.name if dep.nasabah else "",
                    dep.waste_type.name_id if dep.waste_type else "",
                    f"{dep.weight_kg:.3f}" if dep.weight_kg is not None else "",
                    dep.deposit_date.isoformat(),
                    dep.source,
                    dep.created_at.isoformat(),
                ]
            )

        return response
