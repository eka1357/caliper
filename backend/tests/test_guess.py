from caliper import guess


def test_prompt_without_prior_is_unchanged():
    # Cached compare-mode requests without a prior must keep hitting the cache.
    assert guess.prompt_for("How fast is the ball in m/s?") == guess.PROMPT.format(
        question="How fast is the ball in m/s?"
    )
    assert guess.prompt_for("How fast?", "  ") == guess.PROMPT.format(question="How fast?")


def test_prompt_with_prior_adds_the_same_text_caliper_gets():
    text = guess.prompt_for("How long is the box in cm?", "The coin is 0.027 m in diameter.")
    assert text.endswith("\nKnown: The coin is 0.027 m in diameter.")
    assert "Question: How long is the box in cm?" in text
