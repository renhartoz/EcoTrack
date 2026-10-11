import os

import django
import pytest
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


@pytest.fixture(autouse=True)
def enforce_fake_llm_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "fake")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("OCR_SPACE_API_KEY", "")
    settings.LLM_MODE = "fake"
    settings.GROQ_API_KEY = ""
    settings.OCR_SPACE_API_KEY = ""
