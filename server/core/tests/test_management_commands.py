import json
from decimal import Decimal

import pytest
from django.core.management import CommandError, call_command

from core.models import BankSampah, Nasabah, WasteType
from deposits.models import Deposit


@pytest.fixture
def commands_setup(db):
    wt_pet = WasteType.objects.create(code="pet", name_id="Plastik PET")
    wt_kardus = WasteType.objects.create(code="kardus", name_id="Kardus")
    wt_besi = WasteType.objects.create(code="besi", name_id="Besi")
    return {"pet": wt_pet, "kardus": wt_kardus, "besi": wt_besi}


def test_load_emission_factors_success(commands_setup, tmp_path):
    factors_data = [
        {
            "code": "pet",
            "factor": 1.500,
            "source": "IPCC 2006",
            "note": "Avoided virgin PET emissions",
        },
        {
            "code": "kardus",
            "factor": 0.800,
            "source": "KLHK 2024",
            "note": "Avoided landfill methane",
        },
    ]
    file_path = tmp_path / "emission_factors.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(factors_data, f)

    call_command("load_emission_factors", str(file_path))

    wt_pet = WasteType.objects.get(code="pet")
    assert wt_pet.emission_factor_kgco2e_per_kg == Decimal("1.500")
    assert wt_pet.emission_factor_source == "IPCC 2006"

    wt_kardus = WasteType.objects.get(code="kardus")
    assert wt_kardus.emission_factor_kgco2e_per_kg == Decimal("0.800")
    assert wt_kardus.emission_factor_source == "KLHK 2024"

    wt_besi = WasteType.objects.get(code="besi")
    assert wt_besi.emission_factor_kgco2e_per_kg is None


def test_load_emission_factors_dict_format(commands_setup, tmp_path):
    factors_data = {
        "pet": {
            "factor": 1.25,
            "source": "IPCC 2006",
            "note": "PET factor",
        }
    }
    file_path = tmp_path / "emission_factors_dict.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(factors_data, f)

    call_command("load_emission_factors", str(file_path))

    wt_pet = WasteType.objects.get(code="pet")
    assert wt_pet.emission_factor_kgco2e_per_kg == Decimal("1.250")
    assert wt_pet.emission_factor_source == "IPCC 2006"


def test_load_emission_factors_rejects_missing_source(commands_setup, tmp_path):
    factors_data = [
        {
            "code": "pet",
            "factor": 1.500,
            "source": "",
        }
    ]
    file_path = tmp_path / "invalid_factors.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(factors_data, f)

    with pytest.raises(CommandError, match="missing source"):
        call_command("load_emission_factors", str(file_path))


def test_load_emission_factors_nonexistent_file():
    with pytest.raises(CommandError, match="File not found"):
        call_command("load_emission_factors", "non_existent_file.json")


def test_seed_demo_success(commands_setup):
    call_command("seed_demo")

    demo_bank = BankSampah.objects.get(name="Bank Sampah Demo")
    assert demo_bank.is_demo is True

    nasabah_count = Nasabah.objects.filter(bank_sampah=demo_bank).count()
    assert nasabah_count == 12

    deposits = Deposit.objects.filter(bank_sampah=demo_bank)
    assert deposits.count() >= 60
    assert all(d.source == "manual" for d in deposits)

    dates = {d.deposit_date.strftime("%Y-%m") for d in deposits}
    assert len(dates) == 3


def test_seed_demo_idempotent(commands_setup):
    call_command("seed_demo")
    demo_bank = BankSampah.objects.get(name="Bank Sampah Demo")
    first_count = Deposit.objects.filter(bank_sampah=demo_bank).count()

    call_command("seed_demo")
    second_count = Deposit.objects.filter(bank_sampah=demo_bank).count()
    assert first_count == second_count
