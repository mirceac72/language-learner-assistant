from language_learner.models.dialog import (
    Correction,
    DialogRole,
    DialogSession,
    DialogStatus,
    DialogSummary,
    DialogTurn,
)

TARGET_WORDS = ["manger", "boire", "dormir", "partir"]


def make_session() -> DialogSession:
    return DialogSession(
        dialog_id="dlg-1",
        target_words=list(TARGET_WORDS),
        dialog_topic="Au restaurant",
        max_learner_turns=6,
    )


def learner_turn(text: str, words_used: list[str]) -> DialogTurn:
    return DialogTurn(role=DialogRole.LEARNER, text=text, target_words_used=words_used)


def test_session_defaults():
    session = make_session()

    assert session.status is DialogStatus.IN_PROGRESS
    assert session.turns == []
    assert session.end_time is None
    assert session.start_time is not None


def test_dialog_turn_defaults():
    turn = DialogTurn(role=DialogRole.SYSTEM, text="Salut !")

    assert turn.corrections == []
    assert turn.target_words_used == []
    assert turn.review_score is None


def test_learner_turn_count_counts_only_learner_turns():
    session = make_session()
    session.turns.append(DialogTurn(role=DialogRole.SYSTEM, text="Bonjour !"))
    assert session.learner_turn_count == 0

    session.turns.append(learner_turn("J'ai mangé", ["manger"]))
    session.turns.append(DialogTurn(role=DialogRole.SYSTEM, text="Bien !"))
    session.turns.append(learner_turn("J'ai bu", ["boire"]))

    assert session.learner_turn_count == 2


def test_words_used_keeps_order_of_first_use():
    session = make_session()
    session.turns.append(learner_turn("J'ai bu et mangé", ["boire", "manger"]))
    session.turns.append(learner_turn("J'ai mangé encore", ["manger"]))

    assert session.words_used == ["boire", "manger"]


def test_words_used_ignores_system_turns_and_words_outside_target_words():
    session = make_session()
    session.turns.append(
        DialogTurn(
            role=DialogRole.SYSTEM,
            text="Tu as mangé ?",
            target_words_used=["manger"],
        )
    )
    session.turns.append(learner_turn("J'ai mangé", ["manger", "avion"]))

    assert session.words_used == ["manger"]


def test_words_remaining_shrinks_and_never_contains_a_word_twice():
    session = make_session()
    assert session.words_remaining == TARGET_WORDS

    session.turns.append(learner_turn("J'ai mangé", ["manger"]))
    assert session.words_remaining == ["boire", "dormir", "partir"]

    session.turns.append(learner_turn("J'ai bu", ["boire", "boire"]))
    assert session.words_remaining == ["dormir", "partir"]

    session.turns.append(learner_turn("J'ai dormi", ["dormir"]))
    session.turns.append(learner_turn("Je pars", ["partir"]))
    assert session.words_remaining == []


def test_dialog_summary_holds_wrap_up_data():
    correction = Correction(
        original="j'ai mange",
        corrected="j'ai mangé",
        explanation="Accent aigu sur le participe passé.",
    )
    summary = DialogSummary(
        words_used=["manger"],
        words_not_used=["boire"],
        corrections=[correction],
        learner_turns=1,
    )

    assert summary.words_used == ["manger"]
    assert summary.words_not_used == ["boire"]
    assert summary.corrections == [correction]
    assert summary.learner_turns == 1
