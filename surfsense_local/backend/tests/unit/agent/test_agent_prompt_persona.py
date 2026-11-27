from modules.agent.engines.claude_code.tool_names import for_claude
from modules.agent.opencode_config import agent_prompt
from modules.persona.store import agent_persona_text, save_agent_persona, save_persona


def test_without_a_persona_the_agent_prompt_is_unchanged() -> None:
    """A user who wrote none gets the prompt the agent always had."""
    base = agent_prompt()

    assert "style note" not in base


def test_the_persona_is_added_after_the_agents_own_instructions() -> None:
    """Facts, citations and tool rules come first; the persona only sets tone."""
    base = agent_prompt()
    save_persona("Call me Rose.")

    prompt = agent_prompt()

    assert prompt.startswith(base)
    assert prompt.endswith("Call me Rose.")
    assert "tone only" in prompt


def test_the_claude_code_agent_reads_the_same_persona() -> None:
    """Both engines build their instructions from the one function."""
    save_persona("Call me Rose.")

    assert for_claude(agent_prompt()).endswith("Call me Rose.")


def test_an_agent_persona_replaces_the_shared_one_for_the_agent() -> None:
    """A small model follows a short note, so the agent can have its own."""
    save_persona("Long voice with many rules.")
    save_agent_persona("Short voice.")

    prompt = agent_prompt()

    assert prompt.endswith("Short voice.")
    assert "Long voice" not in prompt
    assert "tone only" in prompt


def test_clearing_the_agent_persona_returns_to_the_shared_one() -> None:
    """Emptying the agent's box is how its note is turned off."""
    save_persona("Call me Rose.")
    save_agent_persona("Short voice.")

    save_agent_persona("")

    assert agent_persona_text() == ""
    assert agent_prompt().endswith("Call me Rose.")


def test_an_agent_persona_alone_still_reaches_the_agent() -> None:
    """The agent's note does not need a shared persona beside it."""
    save_agent_persona("Short voice.")

    assert agent_prompt().endswith("Short voice.")
