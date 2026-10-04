from django.http import Http404
from django.shortcuts import get_object_or_404


class BankScopedMixin:
    def get_bank(self):
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return None
        return getattr(user, "bank_sampah", None)

    def get_scoped_object_or_404(self, model_or_queryset, **kwargs):
        bank = self.get_bank()
        if bank is None:
            raise Http404
        queryset = (
            model_or_queryset
            if hasattr(model_or_queryset, "filter")
            else model_or_queryset.objects
        )
        return get_object_or_404(queryset.filter(bank_sampah=bank), **kwargs)
