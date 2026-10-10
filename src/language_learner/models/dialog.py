# Dialog Data Models
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DialogRole(Enum):
    """Who produced a dialog turn"""

    SYSTEM = "system"
    LEARNER = "learner"


class DialogStatus(Enum):
    """Lifecycle status of a dialog session"""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class Correction:
    """One explicit correction of a learner error, shown inside the system turn"""

    original: str  # exact substring of the learner message
    corrected: str
    explanation: str  # French, at most 20 words


@dataclass
class DialogTurn:
    """One message in the dialog"""

    role: DialogRole
    text: str
    corrections: list[Correction] = field(default_factory=list)  # system turns only
    target_words_used: list[str] = field(default_factory=list)  # learner turns only
    review_score: int | None = None  # system turns only


@dataclass
class DialogSession:
    """A dialog practice session built around a set of target words"""

    dialog_id: str
    target_words: list[str]
    dialog_topic: str  # fictional, model-written, reviewed
    max_learner_turns: int
    turns: list[DialogTurn] = field(default_factory=list)
    status: DialogStatus = DialogStatus.IN_PROGRESS
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None

    @property
    def learner_turn_count(self) -> int:
        """Number of learner turns recorded so far"""
        return sum(1 for turn in self.turns if turn.role is DialogRole.LEARNER)

    @property
    def words_used(self) -> list[str]:
        """Target words used correctly, in order of first use, without duplicates"""
        used: list[str] = []
        for turn in self.turns:
            if turn.role is not DialogRole.LEARNER:
                continue
            for word in turn.target_words_used:
                if word in self.target_words and word not in used:
                    used.append(word)
        return used

    @property
    def words_remaining(self) -> list[str]:
        """Target words not used yet, in target order"""
        used = self.words_used
        return [word for word in self.target_words if word not in used]


@dataclass
class DialogSummary:
    """Wrap-up data for a completed dialog"""

    words_used: list[str]
    words_not_used: list[str]
    corrections: list[Correction]
    learner_turns: int
