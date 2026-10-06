import io

import pytest
from django.core.management import CommandError, call_command
from PIL import Image


def test_probe_providers_missing_file():
    with pytest.raises(CommandError, match="Image file not found"):
        call_command("probe_providers", "--image", "non_existent_file.jpg")


def test_probe_providers_skipped_when_keys_blank(tmp_path):
    img_path = tmp_path / "sample.jpg"
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    img.save(str(img_path), format="JPEG")

    out = io.StringIO()
    call_command("probe_providers", "--image", str(img_path), stdout=out)
    output = out.getvalue()
    assert "EcoTrack Provider Probe" in output
    assert "SKIPPED: GROQ_API_KEY is not configured" in output
    assert "SKIPPED: OCR_SPACE_API_KEY is not configured" in output
