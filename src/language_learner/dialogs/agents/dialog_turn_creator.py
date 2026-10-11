"""Dialog turn creator agent.

Produces one candidate system turn per call with structured output, then
filters the parsed candidate deterministically (target-word normalisation
and membership, correction rules). Implements ``Creator[DialogTurnOutput]``
for the generic ``ReviewLoopWorkflow``; the reviewer scores the filtered
candidate.
"""

import json
import logging
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from language_learner.core.llm_interface import LLMClient
from language_learner.dialogs.dialog_prompts import build_creator_prompt
from language_learner.exceptions import DialogTurnError
from language_learner.models.dialog import Correction, DialogSession

logger = logging.getLogger(__name__)


class CorrectionOutput(BaseModel):
    """One explicit correction proposed by the turn creator."""

    model_config = ConfigDict(extra="forbid")

    original: str
    corrected: str
    explanation: str


class DialogTurnOutput(BaseModel):
    """Structured output of the turn creator: the reply plus bookkeeping."""

    model_config = ConfigDict(extra="forbid")

    reply: str
    corrections: list[CorrectionOutput]
    target_words_used: list[str]


@dataclass
class DialogTurnContext:
    """Everything the turn creator and reviewer need for one turn."""

    session: DialogSession
    learner_message: str | None  # None means opening turn
    is_closing: bool
    carried_corrections: list[Correction] = field(
        default_factory=list
    )  # closing turn only: the discarded reply's corrections


class DialogTurnCreatorAgent:
    """Implements ``Creator[DialogTurnOutput]``.

    One LLM call with structured output, then parse-step filtering of the
    parsed candidate (word normalisation and membership, correction rules).
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    def create(
        self,
        context: DialogTurnContext,
        previous: DialogTurnOutput | None,
        feedback: str | None,
    ) -> DialogTurnOutput:
        """Return a candidate turn for ``context``.

        On the first attempt ``previous`` and ``feedback`` are None. On later
        attempts they hold the rejected candidate and the reviewer feedback,
        and the prompt asks for an improved candidate. Raises
        ``DialogTurnError`` when the LLM answer is not valid JSON for
        ``DialogTurnOutput``.
        """
        prompt = build_creator_prompt(
            context.session,
            context.learner_message,
            context.is_closing,
            reviewer_feedback=feedback,
            carried_corrections=context.carried_corrections,
            previous_reply=previous.reply if previous is not None else None,
            previous_corrections=(
                [_to_correction(c) for c in previous.corrections]
                if previous is not None
                else None
            ),
        )
        response = self.llm.generate(
            prompt,
            temperature=0.7,
            max_tokens=300,
            response_schema=DialogTurnOutput.model_json_schema(),
        )
        candidate = _parse_turn_output(response)
        return _filter_candidate(candidate, context)


def _to_correction(correction: CorrectionOutput) -> Correction:
    return Correction(
        original=correction.original,
        corrected=correction.corrected,
        explanation=correction.explanation,
    )


def _parse_turn_output(response: str) -> DialogTurnOutput:
    """Parse the LLM answer into a ``DialogTurnOutput``.

    Accepts a bare JSON object or one wrapped in surrounding text (e.g. a
    markdown code fence). Raises ``DialogTurnError`` on invalid JSON or a
    schema mismatch.
    """
    try:
        data = _loads_json_object(response)
    except json.JSONDecodeError as exc:
        raise DialogTurnError(
            f"Turn creator returned non-JSON: {response[:200]}"
        ) from exc
    try:
        return DialogTurnOutput.model_validate(data)
    except ValidationError as exc:
        raise DialogTurnError(
            f"Turn creator output does not match the schema: {exc}"
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


def _filter_candidate(
    candidate: DialogTurnOutput, context: DialogTurnContext
) -> DialogTurnOutput:
    """Apply the parse-step filtering rules to a parsed candidate.

    - Proposed target words are normalised (Unicode NFC, lowercase) and kept
      only when they are in the target set, reported exactly as listed.
    - A correction whose ``original`` is not a case-insensitive substring of
      the learner message is dropped.
    - At most the first surviving correction is kept.
    - The opening turn keeps no corrections. The closing turn does not
      carry a correction (the carried correction is already shown).
    """
    return DialogTurnOutput(
        reply=candidate.reply,
        corrections=_filter_corrections(
            candidate.corrections,
            context.learner_message,
            context.is_closing,
            context.carried_corrections,
        ),
        target_words_used=_filter_target_words(
            candidate.target_words_used, context.session.target_words
        ),
    )


def _filter_target_words(proposed: list[str], target_words: list[str]) -> list[str]:
    listed = {_normalise(word): word for word in target_words}
    kept: list[str] = []
    for word in proposed:
        normalised = _normalise(word)
        if normalised in listed:
            kept.append(listed[normalised])
    return kept


def _normalise(word: str) -> str:
    return unicodedata.normalize("NFC", word).lower()


def _filter_corrections(
    corrections: list[CorrectionOutput],
    learner_message: str | None,
    is_closing: bool,
    carried_corrections: list[Correction],
) -> list[CorrectionOutput]:
    if learner_message is None:
        # Opening turn: there is no learner message to correct.
        return []
    if is_closing and carried_corrections:
        # The carried correction is already shown to the learner.
        return []
    kept: list[CorrectionOutput] = []
    for correction in corrections:
        if not correction.original.strip():
            continue
        if correction.original.lower() not in learner_message.lower():
            continue
        kept.append(correction)
        break  # at most one correction is shown explicitly
    return kept
