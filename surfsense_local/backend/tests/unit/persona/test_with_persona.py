from modules.persona.apply import with_persona


def test_no_persona_leaves_the_instruction_alone() -> None:
    """A user who wrote none gets the prompt exactly as before."""
    assert with_persona("Cite sources.", "") == "Cite sources."


def test_the_persona_follows_the_rules_and_is_limited_to_tone() -> None:
    """Facts and citation rules come first, so a persona cannot override them."""
    result = with_persona("Cite sources.", "Call me Rose.")

    assert result.startswith("Cite sources.")
    assert result.endswith("Call me Rose.")
    assert "tone only" in result
