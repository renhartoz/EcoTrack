from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from core.mixins import BankScopedMixin
from core.models import Nasabah, WasteType
from core.permissions import IsBankOperator
from deposits.models import AuditLog, Deposit
from ingestion.models import ExtractedRow, Upload, UploadImage
from ingestion.serializers import (
    ExtractedRowSerializer,
    ExtractedRowUpdateSerializer,
    UploadDetailSerializer,
    UploadImageCreateSerializer,
    UploadListSerializer,
    UploadTextCreateSerializer,
)
from ingestion.services.pipeline import process_upload
from ingestion.services.preprocess import (
    FileTooLargeError,
    InvalidImageError,
    prepare_image,
)
from ingestion.services.score import compute_row_score
from ingestion.throttling import UploadRateThrottle


class UploadListCreateView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def get_throttles(self):
        if self.request.method == "POST":
            return [UploadRateThrottle()]
        return []

    def get(self, request):
        bank = self.get_bank()
        queryset = Upload.objects.filter(bank_sampah=bank).order_by("-created_at")
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)
        serializer = UploadListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = UploadImageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Validation failed",
                        "details": serializer.errors,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        image_file = serializer.validated_data["image"]
        source_sha256 = serializer.validated_data.get("source_sha256")

        try:
            prepared = prepare_image(image_file)
        except InvalidImageError as exc:
            return Response(
                {
                    "error": {
                        "code": "INVALID_IMAGE",
                        "message": str(exc),
                        "details": {},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except FileTooLargeError as exc:
            return Response(
                {
                    "error": {
                        "code": "FILE_TOO_LARGE",
                        "message": str(exc),
                        "details": {},
                    }
                },
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        bank = self.get_bank()
        upload = Upload.objects.create(
            bank_sampah=bank,
            created_by=request.user,
            source_type="image",
            source_sha256=source_sha256,
            image_sha256=prepared.sha256,
            status="processing",
            processing_started_at=timezone.now(),
        )
        UploadImage.objects.create(
            upload=upload,
            content_type="image/jpeg",
            data=prepared.llm_jpeg,
        )

        upload = process_upload(upload.id)
        return Response(
            UploadDetailSerializer(upload).data,
            status=status.HTTP_201_CREATED,
        )


class UploadTextView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]
    throttle_classes = [UploadRateThrottle]

    def post(self, request):
        serializer = UploadTextCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Validation failed",
                        "details": serializer.errors,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        text = serializer.validated_data["text"]
        source_sha256 = serializer.validated_data.get("source_sha256")
        bank = self.get_bank()

        upload = Upload.objects.create(
            bank_sampah=bank,
            created_by=request.user,
            source_type="text",
            raw_text=text,
            source_sha256=source_sha256,
            status="processing",
            processing_started_at=timezone.now(),
        )

        upload = process_upload(upload.id)
        return Response(
            UploadDetailSerializer(upload).data,
            status=status.HTTP_201_CREATED,
        )


class UploadDetailView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def get(self, request, pk):
        upload = self.get_scoped_object_or_404(Upload, pk=pk)
        return Response(UploadDetailSerializer(upload).data)


class UploadImageView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def get(self, request, pk):
        upload = self.get_scoped_object_or_404(Upload, pk=pk)
        try:
            image_obj = upload.image
        except UploadImage.DoesNotExist:
            raise Http404

        response = HttpResponse(image_obj.data, content_type=image_obj.content_type)
        response["Cache-Control"] = "no-store"
        return response


class UploadRetryView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]
    throttle_classes = [UploadRateThrottle]

    def post(self, request, pk):
        upload = self.get_scoped_object_or_404(Upload, pk=pk)

        with transaction.atomic():
            locked = Upload.objects.select_for_update().get(id=upload.id)
            if locked.status == "processing":
                if (
                    locked.processing_started_at
                    and (timezone.now() - locked.processing_started_at).total_seconds() <= 120
                ):
                    return Response(
                        {
                            "error": {
                                "code": "UPLOAD_PROCESSING",
                                "message": "Upload is currently processing",
                                "details": {},
                            }
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
            locked.status = "processing"
            locked.processing_started_at = timezone.now()
            locked.save(update_fields=["status", "processing_started_at"])

        reprocessed = process_upload(upload.id)
        return Response(UploadDetailSerializer(reprocessed).data)


class UploadConfirmAllView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def post(self, request, pk):
        bank = self.get_bank()
        with transaction.atomic():
            upload = self.get_scoped_object_or_404(Upload.objects.select_for_update(), pk=pk)
            pending_rows = upload.rows.select_for_update().filter(status="pending").order_by("row_index")

            confirmed_count = 0
            skipped_count = 0

            for r in pending_rows:
                has_hard_flags = any(f.get("severity") == "hard" for f in r.flags)
                has_dup_flags = any(
                    f.get("code") in ("DUPLICATE_IN_PAGE", "DUPLICATE_IN_DB") for f in r.flags
                )
                is_eligible = (
                    r.route == "confirm"
                    and not has_hard_flags
                    and not has_dup_flags
                    and r.nasabah_id is not None
                    and r.waste_type_id is not None
                    and r.weight_kg is not None
                    and r.tanggal is not None
                )

                if is_eligible:
                    deposit = Deposit.objects.create(
                        bank_sampah=bank,
                        nasabah_id=r.nasabah_id,
                        waste_type_id=r.waste_type_id,
                        weight_kg=r.weight_kg,
                        deposit_date=r.tanggal,
                        source="confirmed",
                        upload=upload,
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
                            "source": "confirmed",
                        },
                    )
                    r.status = "saved"
                    r.deposit = deposit
                    r.save(update_fields=["status", "deposit"])
                    confirmed_count += 1
                else:
                    skipped_count += 1

        return Response({"confirmed": confirmed_count, "skipped": skipped_count})


class ExtractedRowDetailView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def patch(self, request, pk):
        bank = self.get_bank()
        with transaction.atomic():
            row = get_object_or_404(
                ExtractedRow.objects.select_for_update().filter(upload__bank_sampah=bank),
                pk=pk,
            )
            if row.status != "pending":
                return Response(
                    {"error": {"code": "ROW_NOT_PENDING", "message": "Row is not in pending status."}},
                    status=status.HTTP_409_CONFLICT,
                )

            serializer = ExtractedRowUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            if "nasabah_id" in data:
                n_id = data["nasabah_id"]
                if n_id is not None:
                    try:
                        nasabah = Nasabah.objects.get(id=n_id, bank_sampah=bank)
                        if not nasabah.is_active:
                            return Response(
                                {"error": {"code": "VALIDATION_ERROR", "message": "Nasabah is inactive."}},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                        row.nasabah = nasabah
                    except Nasabah.DoesNotExist:
                        return Response(
                            {"error": {"code": "VALIDATION_ERROR", "message": "Nasabah not found."}},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    row.nasabah = None

            if "waste_type_id" in data:
                w_id = data["waste_type_id"]
                if w_id is not None:
                    try:
                        waste_type = WasteType.objects.get(id=w_id)
                        if not waste_type.is_active:
                            return Response(
                                {"error": {"code": "VALIDATION_ERROR", "message": "Waste type is inactive."}},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                        row.waste_type = waste_type
                    except WasteType.DoesNotExist:
                        return Response(
                            {"error": {"code": "VALIDATION_ERROR", "message": "Waste type not found."}},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    row.waste_type = None

            if "tanggal" in data:
                row.tanggal = data["tanggal"]
            if "weight_kg" in data:
                row.weight_kg = data["weight_kg"]

            row.human_edited = True

            new_flags = [
                f
                for f in row.flags
                if f.get("code")
                not in (
                    "WEIGHT_UNPARSEABLE",
                    "WEIGHT_NONPOSITIVE",
                    "TYPE_UNKNOWN",
                    "NASABAH_UNKNOWN",
                    "DATE_UNPARSEABLE",
                    "AMBIGUOUS_TYPE",
                    "AMBIGUOUS_NASABAH",
                    "WEIGHT_OUT_OF_RANGE",
                    "DATE_OUT_OF_RANGE",
                )
            ]

            max_weight = getattr(settings, "MAX_WEIGHT_KG_PER_ROW", 200.0)
            if row.weight_kg is None:
                new_flags.append({"code": "WEIGHT_UNPARSEABLE", "severity": "hard"})
            elif row.weight_kg <= Decimal("0"):
                new_flags.append({"code": "WEIGHT_NONPOSITIVE", "severity": "hard"})
            elif row.weight_kg > Decimal(str(max_weight)):
                new_flags.append({"code": "WEIGHT_OUT_OF_RANGE", "severity": "soft"})

            if row.waste_type is None:
                new_flags.append({"code": "TYPE_UNKNOWN", "severity": "hard"})

            if row.nasabah is None:
                new_flags.append({"code": "NASABAH_UNKNOWN", "severity": "hard"})

            today = timezone.now().date()
            min_date = today - timedelta(days=400)
            max_date = today + timedelta(days=1)
            if row.tanggal is None:
                new_flags.append({"code": "DATE_UNPARSEABLE", "severity": "hard"})
            elif row.tanggal < min_date or row.tanggal > max_date:
                new_flags.append({"code": "DATE_OUT_OF_RANGE", "severity": "soft"})

            row.flags = new_flags

            has_hard_flags = any(f.get("severity") == "hard" for f in row.flags)
            if not has_hard_flags:
                row.route = "confirm"
            else:
                row.route = "manual"

            row.score = compute_row_score(
                llm_confidence=row.llm_confidence,
                type_score=1.0 if row.waste_type else 0.0,
                name_score=1.0 if row.nasabah else 0.0,
                weight_kg=row.weight_kg,
                date_val=row.tanggal,
                date_quality="explicit" if row.tanggal else "unparseable",
                flags=row.flags,
            )

            row.save()

        return Response(ExtractedRowSerializer(row).data)


class ExtractedRowConfirmView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def post(self, request, pk):
        bank = self.get_bank()
        with transaction.atomic():
            row = get_object_or_404(
                ExtractedRow.objects.select_for_update().filter(upload__bank_sampah=bank),
                pk=pk,
            )
            if row.status != "pending":
                return Response(
                    {"error": {"code": "ROW_NOT_PENDING", "message": "Row is not in pending status."}},
                    status=status.HTTP_409_CONFLICT,
                )

            has_hard_flags = any(f.get("severity") == "hard" for f in row.flags)
            if (
                has_hard_flags
                or row.nasabah is None
                or row.waste_type is None
                or row.weight_kg is None
                or row.tanggal is None
            ):
                return Response(
                    {"error": {"code": "ROW_HAS_HARD_FLAGS", "message": "Row has hard validation flags."}},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            deposit = Deposit.objects.create(
                bank_sampah=bank,
                nasabah=row.nasabah,
                waste_type=row.waste_type,
                weight_kg=row.weight_kg,
                deposit_date=row.tanggal,
                source="confirmed",
                upload=row.upload,
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
                    "source": "confirmed",
                },
            )
            row.status = "saved"
            row.deposit = deposit
            row.save(update_fields=["status", "deposit"])

        return Response(ExtractedRowSerializer(row).data)


class ExtractedRowRejectView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def post(self, request, pk):
        bank = self.get_bank()
        with transaction.atomic():
            row = get_object_or_404(
                ExtractedRow.objects.select_for_update().filter(upload__bank_sampah=bank),
                pk=pk,
            )
            if row.status != "pending":
                return Response(
                    {"error": {"code": "ROW_NOT_PENDING", "message": "Row is not in pending status."}},
                    status=status.HTTP_409_CONFLICT,
                )

            row.status = "rejected"
            row.save(update_fields=["status"])

            AuditLog.objects.create(
                bank_sampah=bank,
                actor=request.user,
                actor_label=request.user.username,
                action="update",
                entity_type="extracted_row",
                entity_id=row.id,
                before={"status": "pending"},
                after={"status": "rejected"},
            )

        return Response(ExtractedRowSerializer(row).data)
