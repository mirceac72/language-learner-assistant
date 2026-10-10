"""Prompt builders for dialog practice.

The four LLM prompt templates live in ``dialogs/prompts/*.txt``; the
builders load them with ``importlib.resources`` and render them with
placeholder replacement (``_render``): a line that is exactly ``{name}``
is a block placeholder (the value's lines, or nothing when the list is
empty); other ``{name}`` occurrences are replaced inline.

The prompt instructions are written in French; this reduces the English
content in the prompt and the risk of English leaking into learner-facing
text. The learner-facing text they produce is intended to be French.
Structured-output field names (``approved``, ``score``, ``feedback``,
``reply``, ``corrections``, ``original``, ``corrected``, ``explanation``,
``target_words_used``, ``topic``) stay English; only the instructions
around them are French.

Each template starts with a unique marker constant, passed in as a
``{..._MARKER}`` placeholder. ``MockLLMClient`` imports the same constants
to recognise the prompts, so the markers cannot drift from the template
text. ``build_wrap_up`` is not an LLM prompt: it is a fixed French
template rendered without any LLM call.
"""

from __future__ import annotations

import json
import re
from functools import cache
from importlib.resources import files
from typing import TYPE_CHECKING, Protocol

from language_learner.models.dialog import (
    Correction,
    DialogRole,
    DialogSession,
    DialogTurn,
)

if TYPE_CHECKING:
    from language_learner.dialogs.agents.dialog_topic_creator import DialogTopicOutput
    from language_learner.dialogs.agents.dialog_turn_creator import DialogTurnOutput

LEARNER_LEVEL = "A2-B1"

# Unique opening substrings of the four LLM prompts. MockLLMClient matches
# prompts on these constants. The turn creator marker needs the "Tu es un"
# prefix because the topic creator prompt also mentions "partenaire de
# conversation".
TURN_CREATOR_MARKER = "Tu es un partenaire de conversation"
TURN_REVIEWER_MARKER = "Tu examines un tour"
TOPIC_CREATOR_MARKER = "Tu prépares le sujet"
TOPIC_REVIEWER_MARKER = "Tu examines le sujet"

# Fallback topic line used when the topic loop did not approve a topic.
GENERIC_TOPIC_LINE = (
    "Sujet : choisis une situation simple de la vie quotidienne "
    "dans laquelle les mots cibles s'intègrent naturellement."
)

# Spliced into the turn creator template via {question_rules}; omitted on
# closing turns, where they would contradict "Ne pose pas de question."
QUESTION_RULES = [
    "- Utilise un des mots pas encore utilisés, ou pose une question qui invite "
    "l'apprenant à l'utiliser.",
    "- Si l'apprenant a écrit en anglais, répondu par un seul mot ou est hors sujet : "
    "réponds",
    "  brièvement, ne corrige pas, et pose une question qui ramène un mot pas encore "
    "utilisé.",
]

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


@cache
def _load_template(name: str) -> str:
    """Load a prompt template from ``dialogs/prompts/{name}.txt``."""
    return (files("language_learner.dialogs") / "prompts" / f"{name}.txt").read_text(
        encoding="utf-8"
    )


def _render(template: str, values: dict[str, str | list[str]]) -> str:
    """Render a prompt template: a line that is exactly ``{name}`` is a
    block placeholder (the value's lines, or nothing when empty); other
    ``{name}`` occurrences are replaced inline; unknown ones are kept.
    """

    def substitute(line: str) -> str:
        def replace(match: re.Match[str]) -> str:
            value = values.get(match.group(1))
            return value if isinstance(value, str) else match.group(0)

        return _PLACEHOLDER_RE.sub(replace, line)

    lines: list[str] = []
    for line in template.splitlines():
        if line.startswith("{") and line.endswith("}"):
            block = values.get(line[1:-1])
            if isinstance(block, list):
                lines.extend(block)
                continue
        lines.append(substitute(line))
    return "\n".join(lines)


def build_creator_prompt(
    session: DialogSession,
    learner_message: str | None,
    is_closing: bool,
    reviewer_feedback: str | None = None,
    carried_corrections: list[Correction] | None = None,
    previous_reply: str | None = None,
    previous_corrections: list[Correction] | None = None,
) -> str:
    """Build the turn creator prompt.

    ``learner_message`` is None for the opening turn. ``is_closing`` selects
    the closing ending rule and drops the question rules.
    ``carried_corrections`` holds the discarded reply's corrections on a
    closing turn that answers a learner message (the words ran out); only
    the first one is shown. ``reviewer_feedback`` with
    ``previous_reply``/``previous_corrections`` is set on retry attempts,
    when the reviewer rejected the previous candidate.
    """
    if session.dialog_topic:
        topic_block = f"Sujet de la conversation :\n{session.dialog_topic}"
    else:
        topic_block = GENERIC_TOPIC_LINE

    if learner_message is None:
        ending_rule = "Commence la conversation par une salutation et une question."
    elif is_closing:
        ending_rule = (
            "Termine la conversation chaleureusement. Ne pose pas de question."
        )
    else:
        ending_rule = "Termine par une question."

    carried_block: list[str] = []
    if is_closing and carried_corrections:
        first = carried_corrections[0]
        carried_block = [
            f"Correction à montrer d'abord : {first.original} → {first.corrected} : "
            f"{_strip_trailing_punctuation(first.explanation)}. "
            "Ne la remets pas dans « corrections » : ce champ doit être une liste vide."
        ]

    feedback_block: list[str] = []
    if reviewer_feedback is not None:
        previous_corrections_json = json.dumps(
            [_correction_dict(c) for c in previous_corrections or []],
            ensure_ascii=False,
        )
        feedback_block = [
            "Un relecteur a rejeté ta réponse précédente. "
            f"Réponse précédente : {_strip_trailing_punctuation(previous_reply)}. "
            f"Corrections précédentes : {previous_corrections_json}. "
            f"Commentaire du relecteur : {_strip_trailing_punctuation(reviewer_feedback)}. "
            "Analyse le commentaire, garde ce qui était juste, corrige ce qui était "
            "faux, et produis une réponse améliorée."
        ]

    history = "\n".join(_format_history_turn(turn) for turn in session.turns)
    if not history:
        history = "(aucun échange)"

    learner_message_block = (
        ["", f"Dernier message de l'apprenant : « {learner_message} »"]
        if learner_message is not None
        else []
    )

    return _render(
        _load_template("turn_creator"),
        {
            "TURN_CREATOR_MARKER": TURN_CREATOR_MARKER,
            "LEARNER_LEVEL": LEARNER_LEVEL,
            "topic_block": topic_block,
            "target_words": ", ".join(session.target_words),
            "words_remaining": ", ".join(session.words_remaining) or "aucun",
            "ending_rule": ending_rule,
            "question_rules": [] if is_closing else QUESTION_RULES,
            "carried_correction_block": carried_block,
            "history": history,
            "learner_message_block": learner_message_block,
            "reviewer_feedback_block": feedback_block,
        },
    )


def build_reviewer_prompt(
    session: DialogSession,
    learner_message: str | None,
    candidate: DialogTurnOutput,
    is_closing: bool,
    approval_threshold: int = 70,
) -> str:
    """Build the turn reviewer prompt.

    The reviewer does not score ``target_words_used``: it is bookkeeping the
    learner never sees, and a borderline word-tracking call must not be able
    to end the dialog.
    """
    if is_closing:
        ending_check = "termine la conversation sans poser de question"
    else:
        ending_check = "se termine par une question"
    learner_line = learner_message if learner_message is not None else "(aucun)"
    corrections_json = json.dumps(
        [_correction_dict(c) for c in candidate.corrections],
        ensure_ascii=False,
    )
    return _render(
        _load_template("turn_reviewer"),
        {
            "TURN_REVIEWER_MARKER": TURN_REVIEWER_MARKER,
            "LEARNER_LEVEL": LEARNER_LEVEL,
            "learner_message": learner_line,
            "target_words": ", ".join(session.target_words),
            "words_remaining": ", ".join(session.words_remaining) or "aucun",
            "reply": candidate.reply,
            "corrections_json": corrections_json,
            "ending_check": ending_check,
            "approval_threshold": str(approval_threshold),
        },
    )


def build_topic_creator_prompt(
    target_words: list[str],
    reviewer_feedback: str | None = None,
    previous_topic: str | None = None,
) -> str:
    """Build the dialog topic creator prompt.

    ``reviewer_feedback`` with ``previous_topic`` is set on retry attempts,
    when the reviewer rejected the previous candidate.
    """
    feedback_block: list[str] = []
    if reviewer_feedback is not None:
        feedback_block = [
            "Un relecteur a rejeté ta réponse précédente. "
            f"Réponse précédente : {_strip_trailing_punctuation(previous_topic)}. "
            f"Commentaire du relecteur : {_strip_trailing_punctuation(reviewer_feedback)}. "
            "Analyse le commentaire, garde ce qui était juste, corrige ce qui était "
            "faux, et produis une réponse améliorée."
        ]
    return _render(
        _load_template("topic_creator"),
        {
            "TOPIC_CREATOR_MARKER": TOPIC_CREATOR_MARKER,
            "LEARNER_LEVEL": LEARNER_LEVEL,
            "target_words": ", ".join(target_words),
            "reviewer_feedback_block": feedback_block,
        },
    )


def build_topic_reviewer_prompt(
    target_words: list[str],
    candidate: DialogTopicOutput,
    approval_threshold: int = 70,
) -> str:
    """Build the dialog topic reviewer prompt."""
    return _render(
        _load_template("topic_reviewer"),
        {
            "TOPIC_REVIEWER_MARKER": TOPIC_REVIEWER_MARKER,
            "LEARNER_LEVEL": LEARNER_LEVEL,
            "target_words": ", ".join(target_words),
            "topic": candidate.topic,
            "approval_threshold": str(approval_threshold),
        },
    )


def build_wrap_up(session: DialogSession) -> str:
    """Build the wrap-up shown after the final turn. No LLM call."""
    words_used = ", ".join(session.words_used) or "aucun"
    words_not_used = ", ".join(session.words_remaining) or "aucun"
    lines = [
        "Bravo, la conversation est terminée !",
        f"Mots utilisés : {words_used}",
        f"Mots à revoir : {words_not_used}",
    ]
    corrections = [
        correction
        for turn in session.turns
        if turn.role is DialogRole.SYSTEM
        for correction in turn.corrections
    ]
    if corrections:
        lines.append("Corrections :")
        lines.extend(
            f"- « {c.original} » → « {c.corrected} » : {c.explanation}"
            for c in corrections
        )
    else:
        lines.append("Corrections : aucune")
    return "\n".join(lines)


def _format_history_turn(turn: DialogTurn) -> str:
    speaker = "Apprenant" if turn.role is DialogRole.LEARNER else "Système"
    return f"{speaker} : {turn.text}"


def _strip_trailing_punctuation(text: str | None) -> str:
    """Drop trailing sentence punctuation so the prompt never doubles it."""
    if text is None:
        return ""
    return text.rstrip(" .?!")


class _CorrectionLike(Protocol):
    """Structural type shared by ``Correction`` and the agents' ``CorrectionOutput``."""

    original: str
    corrected: str
    explanation: str


def _correction_dict(correction: _CorrectionLike) -> dict[str, str]:
    return {
        "original": correction.original,
        "corrected": correction.corrected,
        "explanation": correction.explanation,
    }
