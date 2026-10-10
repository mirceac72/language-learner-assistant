"""Dialogs module for Language Learner Assistant.

This module contains the dialog practice prompts and, later, the dialog
agents and player.

Keep this ``__init__`` to prompt-builder re-exports; re-exporting the
agents or player would create a ``core → dialogs → core`` import cycle.
"""

from .dialog_prompts import (
    LEARNER_LEVEL,
    build_creator_prompt,
    build_reviewer_prompt,
    build_topic_creator_prompt,
    build_topic_reviewer_prompt,
    build_wrap_up,
)

__all__ = [
    "LEARNER_LEVEL",
    "build_creator_prompt",
    "build_reviewer_prompt",
    "build_topic_creator_prompt",
    "build_topic_reviewer_prompt",
    "build_wrap_up",
]
