import pytest
from django.http import Http404
from rest_framework.test import APIRequestFactory

from accounts.models import User
from core.mixins import BankScopedMixin
from core.models import BankSampah, Nasabah
from core.permissions import IsBankOperator


class DummyView(BankScopedMixin):
    def __init__(self, request):
        self.request = request


@pytest.fixture
def banks(db):
    bank_a = BankSampah.objects.create(name="Bank A", is_demo=False)
    bank_b = BankSampah.objects.create(name="Bank B", is_demo=False)
    return bank_a, bank_b


@pytest.fixture
def users_and_nasabah(db, banks):
    bank_a, bank_b = banks
    user_a = User.objects.create_user(
        username="operator_a",
        password="Password123",
        bank_sampah=bank_a,
    )
    user_b = User.objects.create_user(
        username="operator_b",
        password="Password123",
        bank_sampah=bank_b,
    )
    user_no_bank = User.objects.create_user(
        username="no_bank",
        password="Password123",
        bank_sampah=None,
    )
    nasabah_a = Nasabah.objects.create(
        bank_sampah=bank_a,
        name="Nasabah A",
        normalized_name="nasabah a",
    )
    nasabah_b = Nasabah.objects.create(
        bank_sampah=bank_b,
        name="Nasabah B",
        normalized_name="nasabah b",
    )
    return user_a, user_b, user_no_bank, nasabah_a, nasabah_b


@pytest.mark.django_db
def test_bank_scoped_mixin_access_own_bank(users_and_nasabah):
    user_a, _, _, nasabah_a, _ = users_and_nasabah
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = user_a

    view = DummyView(request)
    obj = view.get_scoped_object_or_404(Nasabah, pk=nasabah_a.pk)
    assert obj == nasabah_a


@pytest.mark.django_db
def test_bank_scoped_mixin_cross_bank_access_raises_404(users_and_nasabah):
    user_a, _, _, _, nasabah_b = users_and_nasabah
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = user_a

    view = DummyView(request)
    with pytest.raises(Http404):
        view.get_scoped_object_or_404(Nasabah, pk=nasabah_b.pk)


@pytest.mark.django_db
def test_bank_scoped_mixin_without_bank_raises_404(users_and_nasabah):
    _, _, user_no_bank, nasabah_a, _ = users_and_nasabah
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = user_no_bank

    view = DummyView(request)
    with pytest.raises(Http404):
        view.get_scoped_object_or_404(Nasabah, pk=nasabah_a.pk)


@pytest.mark.django_db
def test_is_bank_operator_permission(users_and_nasabah):
    user_a, _, user_no_bank, _, _ = users_and_nasabah
    permission = IsBankOperator()
    factory = APIRequestFactory()

    request_a = factory.get("/")
    request_a.user = user_a
    assert permission.has_permission(request_a, None) is True

    request_no_bank = factory.get("/")
    request_no_bank.user = user_no_bank
    assert permission.has_permission(request_no_bank, None) is False
