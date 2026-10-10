"""Generic creator/reviewer loop.

A ``ReviewLoopWorkflow`` asks a ``Creator`` for a candidate, has a ``Reviewer``
score it, and, while the reviewer rejects and attempts remain, asks the creator
for an improved candidate built from the previous one and the reviewer feedback.
A candidate is accepted only when the verdict is approved and its score is at
least the loop's approval threshold (``APPROVAL_THRESHOLD`` by default);
anything else counts as a rejection. When the attempt limit is reached
without approval, the loop ends without an
approved candidate (``approved=False``, ``candidate=None``) and the caller
decides what to do next. The loop is content-agnostic: dialog turns, dialog
topics and, later, other generated artefacts plug in through the two protocols.
"""

import logging
from dataclasses import dataclass
from operator import add
from typing import Annotated, Any, Protocol, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

APPROVAL_THRESHOLD = 70


class ReviewVerdict(BaseModel):
    """Reviewer output. Also usable as the JSON schema handed to LLM reviewers."""

    # extra="forbid" emits "additionalProperties": false, required by Mistral's
    # strict json_schema structured output mode.
    model_config = ConfigDict(extra="forbid")

    approved: bool
    score: int = Field(..., ge=0, le=100)
    feedback: str


class Creator[C](Protocol):
    """Produces a candidate, and improves it when given reviewer feedback."""

    def create(self, context: Any, previous: C | None, feedback: str | None) -> C:
        """Return a candidate for ``context``.

        On the first attempt ``previous`` and ``feedback`` are ``None``. On later
        attempts they hold the rejected candidate and the reviewer feedback, and
        the creator is expected to return an improved candidate.
        """
        ...


class Reviewer[C_contra](Protocol):
    """Scores a candidate for a context."""

    def review(self, context: Any, candidate: C_contra) -> ReviewVerdict:
        """Return a verdict. May run deterministic checks and skip any LLM call."""
        ...


@dataclass
class ReviewLoopResult[C]:
    """Outcome of one loop run."""

    candidate: C | None  # None when the attempt limit was reached without approval
    verdict: ReviewVerdict | None  # None together with candidate
    attempts: int
    approved: bool  # False when the attempt limit was reached without approval
    candidates: list[tuple[C, ReviewVerdict]]  # every attempt, in order


class ReviewLoopState(TypedDict):
    """LangGraph state for one loop run."""

    context: Any
    candidate: Any | None
    verdict: ReviewVerdict | None
    candidates: Annotated[list[tuple[Any, ReviewVerdict]], add]
    attempt: int


class ReviewLoopWorkflow[C]:
    """Creator → reviewer → improve on feedback.

    A candidate is accepted only with an approved verdict scoring at least the
    loop's ``approval_threshold`` (``APPROVAL_THRESHOLD`` by default). The loop
    ends without an approved candidate when the attempt limit is reached.
    """

    def __init__(
        self,
        creator: Creator[C],
        reviewer: Reviewer[C],
        max_attempts: int = 2,
        approval_threshold: int = APPROVAL_THRESHOLD,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.creator = creator
        self.reviewer = reviewer
        self.max_attempts = max_attempts
        self.approval_threshold = approval_threshold
        self._graph = self._build_graph().compile()

    def run(self, context: Any) -> ReviewLoopResult[C]:
        """Run the loop for ``context`` and return the outcome.

        On approval the result holds the approved candidate. When the attempt
        limit is reached without approval the result holds ``approved=False``
        with ``candidate=None``. Exceptions raised by the creator or the
        reviewer propagate unchanged.
        """
        initial: ReviewLoopState = {
            "context": context,
            "candidate": None,
            "verdict": None,
            "candidates": [],
            "attempt": 0,
        }
        # Each attempt is two graph steps (creator, reviewer); the exhausted
        # node adds one. LangGraph needs a little headroom on top.
        final = self._graph.invoke(
            initial, config={"recursion_limit": 2 * self.max_attempts + 3}
        )
        candidate, verdict = final["candidate"], final["verdict"]
        return ReviewLoopResult(
            candidate=candidate,
            verdict=verdict,
            attempts=final["attempt"],
            approved=verdict is not None and verdict.approved,
            candidates=final["candidates"],
        )

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(ReviewLoopState)
        graph.add_node("creator", self._creator_node)
        graph.add_node("reviewer", self._reviewer_node)
        graph.add_node("exhausted", self._exhausted_node)
        graph.set_entry_point("creator")
        graph.add_edge("creator", "reviewer")
        graph.add_conditional_edges(
            "reviewer",
            self._after_review,
            {"done": END, "retry": "creator", "exhausted": "exhausted"},
        )
        graph.add_edge("exhausted", END)
        return graph

    def _creator_node(self, state: ReviewLoopState) -> dict[str, Any]:
        attempt = state["attempt"] + 1
        verdict = state["verdict"]
        logger.debug("Review loop attempt %d/%d", attempt, self.max_attempts)
        candidate = self.creator.create(
            state["context"],
            state["candidate"],
            verdict.feedback if verdict is not None else None,
        )
        return {"candidate": candidate, "attempt": attempt}

    def _reviewer_node(self, state: ReviewLoopState) -> dict[str, Any]:
        candidate = state["candidate"]
        verdict = self.reviewer.review(state["context"], candidate)
        logger.debug(
            "Review loop attempt %d scored %d (approved=%s)",
            state["attempt"],
            verdict.score,
            verdict.approved,
        )
        return {
            "verdict": verdict,
            "candidates": [(candidate, verdict)],
        }

    def _after_review(self, state: ReviewLoopState) -> str:
        verdict = state["verdict"]
        if verdict.approved and verdict.score >= self.approval_threshold:
            return "done"
        if state["attempt"] < self.max_attempts:
            return "retry"
        return "exhausted"

    @staticmethod
    def _exhausted_node(state: ReviewLoopState) -> dict[str, Any]:
        logger.warning(
            "Review loop exhausted %d attempts without approval",
            state["attempt"],
        )
        return {"candidate": None, "verdict": None}
