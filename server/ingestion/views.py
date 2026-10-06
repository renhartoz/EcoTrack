from django.db import transaction
from django.http import Http404, HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from core.mixins import BankScopedMixin
from core.permissions import IsBankOperator
from ingestion.models import Upload, UploadImage
from ingestion.serializers import (
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
