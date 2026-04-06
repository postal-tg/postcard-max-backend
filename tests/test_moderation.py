from postcard_backend.core.config import Settings
from postcard_backend.services.moderation import moderate_prompt


def test_prompt_is_blocked_when_term_matches() -> None:
    settings = Settings(prompt_blocklist="violence,gore")
    result = moderate_prompt("A postcard about cinematic violence", settings)

    assert result.is_allowed is False
    assert result.matched_term == "violence"


def test_prompt_is_allowed_when_no_terms_match() -> None:
    settings = Settings(prompt_blocklist="violence,gore")
    result = moderate_prompt("A postcard about a cozy spring picnic", settings)

    assert result.is_allowed is True
    assert result.matched_term is None


def test_word_boundary_prevents_false_positive_for_latin_terms() -> None:
    settings = Settings(prompt_blocklist="sex")
    result = moderate_prompt("A postcard about Sussex by the sea", settings)

    assert result.is_allowed is True
