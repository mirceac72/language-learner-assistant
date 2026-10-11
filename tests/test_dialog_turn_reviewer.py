"""Tests for the dialog turn reviewer agent. Stub and mock LLM, no API calls."""

import json

import pytest

from language_learner.core.mock_llm import MockLLMClient
from language_learner.core.review_loop import ReviewVerdict
from language_learner.dialogs.agents.dialog_turn_creator import (
    DialogTurnContext,
    DialogTurnOutput,
)
from language_learner.dialogs.agents.dialog_turn_reviewer import (
    MAX_REPLY_SENTENCES,
    DialogTurnReviewerAgent,
)
from language_learner.dialogs.dialog_prompts import TURN_REVIEWER_MARKER
from language_learner.exceptions import DialogTurnError
from language_learner.models.dialog import DialogSession

TARGET_WORDS = ["canicule", "sécheresse", "prévenir", "chaleur"]


class StubLLM:
    """Records generate() calls and returns a canned response."""

    def __init__(self, response: str):
        self.response = response
        self.calls: list[dict] = []

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        response_schema: dict | None = None,
    ) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_schema": response_schema,
            }
        )
        return self.response


def make_session() -> DialogSession:
    return DialogSession(
        dialog_id="dlg-1",
        target_words=list(TARGET_WORDS),
        dialog_topic="Il fait très chaud en été.",
        max_learner_turns=6,
    )


def make_context(
    learner_message: str | None = "Oui, il fait chaud.", is_closing: bool = False
) -> DialogTurnContext:
    return DialogTurnContext(
        session=make_session(),
        learner_message=learner_message,
        is_closing=is_closing,
    )


def make_candidate(reply: str = "Bien ! Et chez toi ?") -> DialogTurnOutput:
    return DialogTurnOutput(reply=reply, corrections=[], target_words_used=[])


def verdict_json(
    approved: bool = True, score: int = 85, feedback: str = "Bien."
) -> str:
    return json.dumps(
        {"approved": approved, "score": score, "feedback": feedback},
        ensure_ascii=False,
    )


# Hard-failure short-circuit: no LLM call


def test_empty_reply_is_rejected_without_llm_call():
    stub = StubLLM(verdict_json())
    reviewer = DialogTurnReviewerAgent(stub)

    verdict = reviewer.review(make_context(), make_candidate(reply="   "))

    assert verdict.approved is False
    assert verdict.score == 0
    assert verdict.feedback
    assert stub.calls == []


def test_overlong_reply_is_rejected_without_llm_call():
    stub = StubLLM(verdict_json())
    reviewer = DialogTurnReviewerAgent(stub)
    reply = " ".join(f"Phrase {i}." for i in range(1, MAX_REPLY_SENTENCES + 2))

    verdict = reviewer.review(make_context(), make_candidate(reply=reply))

    assert verdict.approved is False
    assert verdict.score == 0
    assert verdict.feedback
    assert stub.calls == []


def test_reply_at_the_sentence_limit_reaches_the_llm():
    stub = StubLLM(verdict_json())
    reviewer = DialogTurnReviewerAgent(stub)
    reply = " ".join(f"Phrase {i}." for i in range(1, MAX_REPLY_SENTENCES + 1))

    verdict = reviewer.review(make_context(), make_candidate(reply=reply))

    assert verdict.approved is True
    assert len(stub.calls) == 1


# LLM review


def test_review_calls_the_llm_with_the_reviewer_prompt():
    stub = StubLLM(verdict_json(score=90, feedback="Très bien."))
    reviewer = DialogTurnReviewerAgent(stub)
    candidate = make_candidate(reply="Bien ! Et chez toi ?")

    verdict = reviewer.review(make_context(), candidate)

    assert verdict == ReviewVerdict(approved=True, score=90, feedback="Très bien.")
    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert TURN_REVIEWER_MARKER in call["prompt"]
    assert "Bien ! Et chez toi ?" in call["prompt"]
    assert "score >= 70" in call["prompt"]
    assert call["temperature"] == 0.3
    assert call["max_tokens"] == 200
    assert call["response_schema"] == ReviewVerdict.model_json_schema()


def test_review_uses_the_configured_approval_threshold():
    stub = StubLLM(verdict_json())
    reviewer = DialogTurnReviewerAgent(stub, approval_threshold=90)

    reviewer.review(make_context(), make_candidate())

    prompt = stub.calls[0]["prompt"]
    assert "score >= 90" in prompt
    assert "score >= 70" not in prompt


def test_review_passes_the_closing_turn_through_to_the_prompt():
    stub = StubLLM(verdict_json())
    reviewer = DialogTurnReviewerAgent(stub)

    reviewer.review(make_context(is_closing=True), make_candidate())

    prompt = stub.calls[0]["prompt"]
    assert "termine la conversation sans poser de question" in prompt


def test_review_does_not_score_target_words_used():
    stub = StubLLM(verdict_json())
    reviewer = DialogTurnReviewerAgent(stub)
    candidate = DialogTurnOutput(
        reply="Bien !",
        corrections=[],
        target_words_used=["n'importe quoi"],
    )

    verdict = reviewer.review(make_context(), candidate)

    assert verdict.approved is True
    assert "target_words_used" not in stub.calls[0]["prompt"]


def test_review_with_mock_llm_client():
    reviewer = DialogTurnReviewerAgent(MockLLMClient())

    verdict = reviewer.review(make_context(), make_candidate())

    assert verdict.approved is True
    assert verdict.score >= 70


def test_review_raises_dialog_turn_error_on_non_json():
    stub = StubLLM("Ce n'est pas du JSON.")
    reviewer = DialogTurnReviewerAgent(stub)

    with pytest.raises(DialogTurnError, match="non-JSON"):
        reviewer.review(make_context(), make_candidate())


def test_review_raises_dialog_turn_error_on_schema_mismatch():
    stub = StubLLM('{"approved": true, "score": 101, "feedback": "Hors limites."}')
    reviewer = DialogTurnReviewerAgent(stub)

    with pytest.raises(DialogTurnError, match="schema"):
        reviewer.review(make_context(), make_candidate())
