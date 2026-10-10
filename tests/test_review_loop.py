"""Tests for the generic creator/reviewer loop. No LLM involved."""

from dataclasses import dataclass, field

import pytest
from pydantic import ValidationError

from language_learner.core.review_loop import (
    ReviewLoopResult,
    ReviewLoopWorkflow,
    ReviewVerdict,
)


@dataclass
class StubCreator:
    """Returns numbered candidates and records every call."""

    calls: list[tuple[str, str | None, str | None]] = field(default_factory=list)
    fail_on_attempt: int | None = None

    def create(self, context: str, previous: str | None, feedback: str | None) -> str:
        self.calls.append((context, previous, feedback))
        if self.fail_on_attempt == len(self.calls):
            raise RuntimeError("creator failed")
        return f"candidate-{len(self.calls)}"


@dataclass
class StubReviewer:
    """Returns scripted scores in order; approved when score >= 70."""

    scores: list[int]
    calls: list[tuple[str, str]] = field(default_factory=list)
    fail: bool = False

    def review(self, context: str, candidate: str) -> ReviewVerdict:
        self.calls.append((context, candidate))
        if self.fail:
            raise RuntimeError("reviewer failed")
        score = self.scores[len(self.calls) - 1]
        return ReviewVerdict(
            approved=score >= 70, score=score, feedback=f"feedback-{len(self.calls)}"
        )


@dataclass
class StaticReviewer:
    """Always returns the same verdict, even one that disagrees with itself."""

    verdict: ReviewVerdict

    def review(self, context: str, candidate: str) -> ReviewVerdict:
        return self.verdict


def run(scores: list[int], max_attempts: int = 2, **creator_kwargs):
    creator = StubCreator(**creator_kwargs)
    reviewer = StubReviewer(scores=scores)
    loop = ReviewLoopWorkflow(creator, reviewer, max_attempts=max_attempts)
    return loop.run("ctx"), creator, reviewer


def test_approved_on_first_attempt():
    result, creator, reviewer = run([85])

    assert isinstance(result, ReviewLoopResult)
    assert result.candidate == "candidate-1"
    assert result.approved is True
    assert result.attempts == 1
    assert result.verdict.score == 85
    assert result.candidates == [("candidate-1", result.verdict)]
    assert creator.calls == [("ctx", None, None)]
    assert reviewer.calls == [("ctx", "candidate-1")]


def test_rejected_then_improved_candidate_approved():
    result, creator, reviewer = run([40, 80])

    assert result.candidate == "candidate-2"
    assert result.approved is True
    assert result.attempts == 2
    assert len(result.candidates) == 2
    # Second create receives the rejected candidate and the reviewer feedback.
    assert creator.calls == [("ctx", None, None), ("ctx", "candidate-1", "feedback-1")]
    assert reviewer.calls == [("ctx", "candidate-1"), ("ctx", "candidate-2")]


def test_all_attempts_rejected_ends_without_candidate():
    result, creator, _ = run([40, 60, 50], max_attempts=3)

    assert result.candidate is None
    assert result.verdict is None
    assert result.approved is False
    assert result.attempts == 3
    assert [c for c, _ in result.candidates] == [
        "candidate-1",
        "candidate-2",
        "candidate-3",
    ]
    assert len(creator.calls) == 3


def test_single_attempt_rejected_ends_without_candidate():
    result, creator, _ = run([10], max_attempts=1)

    assert result.candidate is None
    assert result.verdict is None
    assert result.approved is False
    assert result.attempts == 1
    assert len(creator.calls) == 1


def test_approved_true_below_threshold_is_treated_as_rejection():
    reviewer = StaticReviewer(ReviewVerdict(approved=True, score=50, feedback="ok"))
    loop = ReviewLoopWorkflow(StubCreator(), reviewer, max_attempts=2)

    result = loop.run("ctx")

    assert result.approved is False
    assert result.candidate is None
    assert result.attempts == 2


def test_approved_false_above_threshold_is_treated_as_rejection():
    reviewer = StaticReviewer(ReviewVerdict(approved=False, score=95, feedback="no"))
    loop = ReviewLoopWorkflow(StubCreator(), reviewer, max_attempts=1)

    result = loop.run("ctx")

    assert result.approved is False
    assert result.candidate is None
    assert result.attempts == 1


def test_score_at_threshold_with_approved_true_is_accepted():
    reviewer = StaticReviewer(ReviewVerdict(approved=True, score=70, feedback="ok"))
    loop = ReviewLoopWorkflow(StubCreator(), reviewer)

    result = loop.run("ctx")

    assert result.approved is True
    assert result.candidate == "candidate-1"
    assert result.attempts == 1


def test_custom_approval_threshold_is_enforced():
    reviewer = StaticReviewer(ReviewVerdict(approved=True, score=80, feedback="ok"))
    loop = ReviewLoopWorkflow(StubCreator(), reviewer, approval_threshold=90)

    result = loop.run("ctx")

    assert result.approved is False
    assert result.candidate is None
    assert result.attempts == 2


def test_creator_exception_propagates():
    with pytest.raises(RuntimeError, match="creator failed"):
        run([40, 80], fail_on_attempt=2)


def test_reviewer_exception_propagates():
    creator = StubCreator()
    reviewer = StubReviewer(scores=[80], fail=True)
    loop = ReviewLoopWorkflow(creator, reviewer)
    with pytest.raises(RuntimeError, match="reviewer failed"):
        loop.run("ctx")


def test_loop_is_reusable_across_runs():
    creator = StubCreator()
    reviewer = StubReviewer(scores=[80, 90])
    loop = ReviewLoopWorkflow(creator, reviewer)

    first = loop.run("first")
    second = loop.run("second")

    assert first.candidate == "candidate-1" and first.attempts == 1
    assert second.candidate == "candidate-2" and second.attempts == 1
    assert second.candidates == [("candidate-2", second.verdict)]


def test_max_attempts_above_default_recursion_limit():
    # 15 attempts is 30 graph steps, above LangGraph's default limit of 25.
    result, _, _ = run([10] * 14 + [90], max_attempts=15)

    assert result.approved is True
    assert result.attempts == 15


def test_max_attempts_must_be_positive():
    with pytest.raises(ValueError):
        ReviewLoopWorkflow(StubCreator(), StubReviewer(scores=[]), max_attempts=0)


def test_review_verdict_schema_is_strict():
    schema = ReviewVerdict.model_json_schema()

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"approved", "score", "feedback"}
    with pytest.raises(ValidationError):
        ReviewVerdict(approved=True, score=101, feedback="")
    with pytest.raises(ValidationError):
        ReviewVerdict(approved=True, score=50, feedback="", extra="no")
