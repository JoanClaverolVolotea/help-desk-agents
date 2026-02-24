from __future__ import annotations

from language_policy import detect_user_language, normalize_language


def test_detect_user_language_returns_spanish() -> None:
    language = detect_user_language("Necesito ayuda con acceso a la cuenta", "en")
    assert language == "es"


def test_detect_user_language_returns_english() -> None:
    language = detect_user_language("I need help with account access", "es")
    assert language == "en"


def test_detect_user_language_keeps_previous_for_ambiguous_text() -> None:
    language = detect_user_language("USDV-176285", "es")
    assert language == "es"


def test_detect_user_language_defaults_to_english_without_previous() -> None:
    language = detect_user_language("USDV-176285", None)
    assert language == "en"


def test_normalize_language_defaults_to_english() -> None:
    assert normalize_language("fr") == "en"
