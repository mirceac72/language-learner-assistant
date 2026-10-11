"""Dialog turn reviewer agent.

Hard-failure short-circuit (empty or overlong reply), then one
LLM review call returning a ``ReviewVerdict``. Implements
``Reviewer[DialogTurnOutput]`` for the generic ``ReviewLoopWorkflow``. The
reviewer scores only what the learner sees (the reply and its corrections);
it does not score ``target_words_used``.
"""

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from language_learner.core.llm_interface import LLMClient
from language_learner.core.review_loop import ReviewVerdict
from language_learner.dialogs.agents.dialog_turn_creator import (
    DialogTurnContext,
    DialogTurnOutput,
)
from language_learner.dialogs.dialog_prompts import build_reviewer_prompt
from language_learner.exceptions import DialogTurnError

logger = logging.getLogger(__name__)

# A reply with more sentences than this is rejected without an LLM call.
MAX_REPLY_SENTENCES = 6

_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")

# Hard-failure feedback, in French like the reviewer prompt.
_EMPTY_REPLY_FEEDBACK = "La réponse est vide. Écris une vraie réponse en français."
_TOO_LONG_REPLY_FEEDBACK = (
    f"La réponse fait plus de {MAX_REPLY_SENTENCES} phrases. "
    "Écris 2 à 4 phrases courtes."
)


class DialogTurnReviewerAgent:
    """Implements ``Reviewer[DialogTurnOutput]``."""

    def __init__(self, llm_client: LLMClient, approval_threshold: int = 70) -> None:
        self.llm = llm_client
        self.approval_threshold = approval_threshold

    def review(
        self, context: DialogTurnContext, candidate: DialogTurnOutput
    ) -> ReviewVerdict:
        """Return a verdict for ``candidate``.

        An empty or overlong reply is rejected without an LLM call. Otherwise
        one LLM call scores the reply and its corrections. Raises
        ``DialogTurnError`` when the LLM answer is not a valid
        ``ReviewVerdict``.
        """
        reply = candidate.reply.strip()
        if not reply:
            return ReviewVerdict(
                approved=False, score=0, feedback=_EMPTY_REPLY_FEEDBACK
            )
        if _sentence_count(reply) > MAX_REPLY_SENTENCES:
            return ReviewVerdict(
                approved=False, score=0, feedback=_TOO_LONG_REPLY_FEEDBACK
            )

        prompt = build_reviewer_prompt(
            context.session,
            context.learner_message,
            candidate,
            context.is_closing,
            approval_threshold=self.approval_threshold,
        )
        response = self.llm.generate(
            prompt,
            temperature=0.3,
            max_tokens=200,
            response_schema=ReviewVerdict.model_json_schema(),
        )
        return _parse_verdict(response)


def _sentence_count(text: str) -> int:
    return len([part for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()])


def _parse_verdict(response: str) -> ReviewVerdict:
    """Parse the LLM answer into a ``ReviewVerdict``.

    Accepts a bare JSON object or one wrapped in surrounding text (e.g. a
    markdown code fence). Raises ``DialogTurnError`` on invalid JSON or a
    schema mismatch.
    """
    try:
        data = _loads_json_object(response)
    except json.JSONDecodeError as exc:
        raise DialogTurnError(
            f"Turn reviewer returned non-JSON: {response[:200]}"
        ) from exc
    try:
        return ReviewVerdict.model_validate(data)
    except ValidationError as exc:
        raise DialogTurnError(
            f"Turn reviewer verdict does not match the schema: {exc}"
        ) from exc


def _loads_json_object(response: str) -> Any:
    """Parse a JSON object from an LLM response, tolerating code fences."""
    text = response.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise json.JSONDecodeError("No JSON object in response", text, 0)
