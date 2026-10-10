from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.mixins import BankScopedMixin
from core.models import Nasabah, WasteType
from core.permissions import IsBankOperator
from core.serializers import NasabahSerializer, WasteTypeSerializer
from ingestion.services.normalize import normalize_text


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class NasabahListCreateView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def get(self, request):
        bank = self.get_bank()
        queryset = Nasabah.objects.filter(bank_sampah=bank).order_by("name")
        q = request.query_params.get("q")
        if q:
            queryset = queryset.filter(name__icontains=q.strip())

        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = NasabahSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        bank = self.get_bank()
        serializer = NasabahSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"]
        norm_name = normalize_text(name)

        if Nasabah.objects.filter(bank_sampah=bank, normalized_name=norm_name).exists():
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "Nasabah already exists."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nasabah = Nasabah.objects.create(
            bank_sampah=bank,
            name=name,
            normalized_name=norm_name,
        )
        return Response(NasabahSerializer(nasabah).data, status=status.HTTP_201_CREATED)


class NasabahDetailView(BankScopedMixin, APIView):
    permission_classes = [IsBankOperator]

    def get(self, request, pk):
        nasabah = self.get_scoped_object_or_404(Nasabah, pk=pk)
        return Response(NasabahSerializer(nasabah).data)

    def patch(self, request, pk):
        bank = self.get_bank()
        nasabah = self.get_scoped_object_or_404(Nasabah, pk=pk)
        serializer = NasabahSerializer(nasabah, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if "name" in serializer.validated_data:
            new_name = serializer.validated_data["name"]
            new_norm = normalize_text(new_name)
            if (
                Nasabah.objects.filter(bank_sampah=bank, normalized_name=new_norm)
                .exclude(pk=nasabah.pk)
                .exists()
            ):
                return Response(
                    {"error": {"code": "VALIDATION_ERROR", "message": "Nasabah already exists."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            nasabah.name = new_name
            nasabah.normalized_name = new_norm

        if "is_active" in serializer.validated_data:
            nasabah.is_active = serializer.validated_data["is_active"]

        nasabah.save()
        return Response(NasabahSerializer(nasabah).data)


class WasteTypeListView(APIView):
    permission_classes = [IsBankOperator]

    def get(self, request):
        types = WasteType.objects.filter(is_active=True).order_by("id")
        serializer = WasteTypeSerializer(types, many=True)
        return Response(serializer.data)
