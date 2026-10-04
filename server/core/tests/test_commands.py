from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.models import User
from core.models import BankSampah


@pytest.mark.django_db
def test_create_operator_creates_bank_and_user():
    out = StringIO()
    call_command(
        "create_operator",
        username="new_operator",
        bank="Bank Sukses",
        city="Sleman",
        password="SecurePassword123",
        stdout=out,
    )

    user = User.objects.get(username="new_operator")
    assert user.check_password("SecurePassword123")
    assert user.bank_sampah is not None
    assert user.bank_sampah.name == "Bank Sukses"
    assert user.bank_sampah.city == "Sleman"
    assert "Successfully created operator" in out.getvalue()


@pytest.mark.django_db
def test_create_operator_duplicate_username_fails():
    bank = BankSampah.objects.create(name="Bank Existing")
    User.objects.create_user(
        username="existing_user",
        password="Password123",
        bank_sampah=bank,
    )

    with pytest.raises(CommandError, match="already exists"):
        call_command(
            "create_operator",
            username="existing_user",
            bank="Bank Another",
            password="NewPassword123",
        )
