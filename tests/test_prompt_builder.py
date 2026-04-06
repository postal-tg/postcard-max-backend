from postcard_backend.core.config import Settings
from postcard_backend.services.prompt_builder import normalize_user_prompt


def test_prompt_is_normalized() -> None:
    settings = Settings()
    result = normalize_user_prompt("  Весенняя   открытка   с котом  ", settings)

    assert result.is_valid is True
    assert result.normalized_text == "Весенняя открытка с котом"
    assert "no visible text" in result.provider_prompt.lower()


def test_prompt_limit_is_enforced() -> None:
    settings = Settings(prompt_text_limit=10)
    result = normalize_user_prompt("x" * 11, settings)

    assert result.is_valid is False
    assert "10" in (result.error_message or "")
