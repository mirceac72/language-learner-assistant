"""Tests for the dialog practice prompt builders and the mock LLM answers."""

import json
from types import SimpleNamespace

from language_learner.core.mock_llm import MockLLMClient
from language_learner.core.review_loop import ReviewVerdict
from language_learner.dialogs.dialog_prompts import (
    GENERIC_TOPIC_LINE,
    LEARNER_LEVEL,
    TOPIC_CREATOR_MARKER,
    TOPIC_REVIEWER_MARKER,
    TURN_CREATOR_MARKER,
    TURN_REVIEWER_MARKER,
    _load_template,
    _render,
    build_creator_prompt,
    build_reviewer_prompt,
    build_topic_creator_prompt,
    build_topic_reviewer_prompt,
    build_wrap_up,
)
from language_learner.models.dialog import (
    Correction,
    DialogRole,
    DialogSession,
    DialogTurn,
)

TARGET_WORDS = ["canicule", "sécheresse", "prévenir", "chaleur"]


def make_session(dialog_topic: str = "Il fait très chaud en été.") -> DialogSession:
    return DialogSession(
        dialog_id="dlg-1",
        target_words=list(TARGET_WORDS),
        dialog_topic=dialog_topic,
        max_learner_turns=6,
    )


def turn_candidate(
    reply: str = "Il fait chaud aujourd'hui. Est-ce qu'il y a une canicule chez toi ?",
    corrections: list | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        reply=reply,
        corrections=corrections or [],
        target_words_used=[],
    )


def correction_stub(original: str, corrected: str, explanation: str) -> SimpleNamespace:
    return SimpleNamespace(
        original=original, corrected=corrected, explanation=explanation
    )


# TC2: creator prompt per turn kind


def test_creator_prompt_opening_turn_has_greeting_rule_and_no_learner_message():
    prompt = build_creator_prompt(
        make_session(), learner_message=None, is_closing=False
    )

    assert "Commence la conversation par une salutation et une question." in prompt
    assert "Dernier message de l'apprenant :" not in prompt
    assert LEARNER_LEVEL in prompt
    for word in TARGET_WORDS:
        assert word in prompt


def test_creator_prompt_normal_turn_ends_with_a_question():
    prompt = build_creator_prompt(
        make_session(), learner_message="Oui, il fait chaud.", is_closing=False
    )

    assert "Termine par une question." in prompt
    assert "Commence la conversation par une salutation" not in prompt
    assert "Termine la conversation chaleureusement" not in prompt
    assert "Dernier message de l'apprenant : « Oui, il fait chaud. »" in prompt
    assert (
        "- Utilise un des mots pas encore utilisés, ou pose une question qui invite "
        "l'apprenant à l'utiliser." in prompt
    )
    assert "pose une question qui ramène un mot pas encore utilisé." in prompt


def test_creator_prompt_closing_turn_has_closing_rule():
    prompt = build_creator_prompt(
        make_session(), learner_message="Oui, il fait chaud.", is_closing=True
    )

    assert "Termine la conversation chaleureusement. Ne pose pas de question." in prompt
    assert "Termine par une question." not in prompt
    # The two rules that ask for a question would contradict the closing rule.
    assert "Utilise un des mots pas encore utilisés, ou pose une question" not in prompt
    assert "pose une question qui ramène un mot pas encore utilisé" not in prompt


def test_creator_prompt_shows_aucun_when_every_word_is_used():
    session = make_session()
    session.turns.append(
        DialogTurn(
            role=DialogRole.LEARNER,
            text="Il fait une canicule, la sécheresse, il faut prévenir, il fait une chaleur.",
            target_words_used=list(TARGET_WORDS),
        )
    )

    prompt = build_creator_prompt(session, learner_message="Merci !", is_closing=True)

    assert "Mots cibles pas encore utilisés : aucun" in prompt


def test_reviewer_prompt_shows_aucun_when_every_word_is_used():
    session = make_session()
    session.turns.append(
        DialogTurn(
            role=DialogRole.LEARNER,
            text="Il fait une canicule, la sécheresse, il faut prévenir, il fait une chaleur.",
            target_words_used=list(TARGET_WORDS),
        )
    )

    prompt = build_reviewer_prompt(
        session, "Merci !", turn_candidate(), is_closing=True
    )

    assert "Pas encore utilisés avant ce tour : aucun" in prompt


def test_creator_prompt_shows_history_and_remaining_words():
    session = make_session()
    session.turns.append(DialogTurn(role=DialogRole.SYSTEM, text="Bonjour !"))
    session.turns.append(
        DialogTurn(
            role=DialogRole.LEARNER,
            text="Il fait une canicule.",
            target_words_used=["canicule"],
        )
    )

    prompt = build_creator_prompt(
        session, learner_message="Et chez toi ?", is_closing=False
    )

    assert "Système : Bonjour !" in prompt
    assert "Apprenant : Il fait une canicule." in prompt
    assert "Mots cibles pas encore utilisés : sécheresse, prévenir, chaleur" in prompt


def test_creator_prompt_empty_history_is_marked():
    prompt = build_creator_prompt(
        make_session(), learner_message=None, is_closing=False
    )

    assert "(aucun échange)" in prompt


def test_creator_prompt_falls_back_to_generic_topic_line_when_topic_is_empty():
    prompt = build_creator_prompt(
        make_session(dialog_topic=""), learner_message=None, is_closing=False
    )

    assert GENERIC_TOPIC_LINE in prompt
    assert "Sujet de la conversation :" not in prompt


def test_creator_prompt_shows_the_dialog_topic():
    prompt = build_creator_prompt(
        make_session(dialog_topic="Tu es à la plage avec des amis."),
        learner_message=None,
        is_closing=False,
    )

    assert "Sujet de la conversation :\nTu es à la plage avec des amis." in prompt


def test_creator_prompt_carries_correction_only_on_closing_turn():
    correction = Correction(
        original="j'ai mange",
        corrected="j'ai mangé",
        explanation="Accent aigu sur le participe passé.",
    )

    closing = build_creator_prompt(
        make_session(),
        learner_message="J'ai mange une pomme.",
        is_closing=True,
        carried_corrections=[correction],
    )
    assert (
        "Correction à montrer d'abord : j'ai mange → j'ai mangé : "
        "Accent aigu sur le participe passé." in closing
    )
    assert (
        "Ne la remets pas dans « corrections » : ce champ doit être une liste vide."
        in closing
    )
    assert "passé.." not in closing

    normal = build_creator_prompt(
        make_session(),
        learner_message="J'ai mange une pomme.",
        is_closing=False,
        carried_corrections=[correction],
    )
    assert "Correction à montrer d'abord" not in normal


def test_creator_prompt_feedback_block_on_retry():
    correction = Correction(
        original="j'ai mange", corrected="j'ai mangé", explanation="Accent aigu."
    )

    prompt = build_creator_prompt(
        make_session(),
        learner_message="J'ai mange une pomme.",
        is_closing=False,
        reviewer_feedback="La réponse est trop longue.",
        previous_reply="Voici une longue réponse.",
        previous_corrections=[correction],
    )

    assert "Un relecteur a rejeté ta réponse précédente." in prompt
    assert "Réponse précédente : Voici une longue réponse." in prompt
    assert "j'ai mangé" in prompt
    assert "Commentaire du relecteur : La réponse est trop longue." in prompt
    assert "Analyse le commentaire" in prompt


def test_creator_prompt_feedback_block_strips_trailing_punctuation():
    prompt = build_creator_prompt(
        make_session(),
        learner_message="J'ai mange une pomme.",
        is_closing=False,
        reviewer_feedback="La réponse est trop longue.",
        previous_reply="Et chez toi ?",
    )

    assert "Réponse précédente : Et chez toi." in prompt
    assert "Commentaire du relecteur : La réponse est trop longue." in prompt
    assert "?." not in prompt
    assert ".." not in prompt


def test_creator_prompt_has_no_feedback_block_on_first_attempt():
    prompt = build_creator_prompt(
        make_session(), learner_message="Bonjour", is_closing=False
    )

    assert "Un relecteur" not in prompt


# Reviewer prompt


def test_reviewer_prompt_contains_candidate_learner_message_and_threshold():
    candidate = turn_candidate(
        corrections=[correction_stub("j'ai mange", "j'ai mangé", "Accent aigu.")]
    )

    prompt = build_reviewer_prompt(
        make_session(), "J'ai mange une pomme.", candidate, is_closing=False
    )

    assert TURN_REVIEWER_MARKER in prompt
    assert "Dernier message de l'apprenant : « J'ai mange une pomme. »" in prompt
    assert "Réponse candidate : « Il fait chaud aujourd'hui." in prompt
    assert '"original": "j\'ai mange"' in prompt
    assert "se termine par une question" in prompt
    assert "score >= 70" in prompt
    for word in TARGET_WORDS:
        assert word in prompt


def test_reviewer_prompt_closing_turn_checks_that_no_question_is_asked():
    prompt = build_reviewer_prompt(
        make_session(), "Merci !", turn_candidate(), is_closing=True
    )

    assert "termine la conversation sans poser de question" in prompt
    assert "se termine par une question" not in prompt


def test_reviewer_prompt_uses_the_configured_approval_threshold():
    prompt = build_reviewer_prompt(
        make_session(),
        "Merci !",
        turn_candidate(),
        is_closing=False,
        approval_threshold=90,
    )

    assert "score >= 90" in prompt
    assert "score >= 70" not in prompt


def test_reviewer_prompt_opening_turn_has_no_learner_message():
    prompt = build_reviewer_prompt(
        make_session(), None, turn_candidate(), is_closing=False
    )

    assert "Dernier message de l'apprenant : « (aucun) »" in prompt


# TC16: topic prompts


def test_topic_creator_prompt_contains_level_words_length_limit_and_fictional_rule():
    prompt = build_topic_creator_prompt(TARGET_WORDS)

    assert TOPIC_CREATOR_MARKER in prompt
    assert LEARNER_LEVEL in prompt
    for word in TARGET_WORDS:
        assert word in prompt
    assert "15 mots maximum" in prompt
    assert "fictive" in prompt
    assert "Un relecteur" not in prompt


def test_topic_creator_prompt_feedback_block_on_retry():
    prompt = build_topic_creator_prompt(
        TARGET_WORDS,
        reviewer_feedback="Le sujet n'est pas fictif.",
        previous_topic="Tu parles de l'actualité.",
    )

    assert "Un relecteur a rejeté ta réponse précédente." in prompt
    assert "Réponse précédente : Tu parles de l'actualité." in prompt
    assert "Commentaire du relecteur : Le sujet n'est pas fictif." in prompt


def test_topic_creator_prompt_feedback_block_strips_trailing_punctuation():
    prompt = build_topic_creator_prompt(
        TARGET_WORDS,
        reviewer_feedback="Le sujet n'est pas fictif.",
        previous_topic="Tu parles de l'actualité.",
    )

    assert "Réponse précédente : Tu parles de l'actualité." in prompt
    assert "Commentaire du relecteur : Le sujet n'est pas fictif." in prompt
    assert ".." not in prompt


def test_topic_reviewer_prompt_contains_words_and_fit_check():
    candidate = SimpleNamespace(
        topic="Tu passes l'été chez ta grand-mère à la campagne."
    )

    prompt = build_topic_reviewer_prompt(TARGET_WORDS, candidate)

    assert TOPIC_REVIEWER_MARKER in prompt
    for word in TARGET_WORDS:
        assert word in prompt
    assert "Tu passes l'été chez ta grand-mère à la campagne." in prompt
    assert "Chaque mot cible a une place naturelle" in prompt
    assert "score >= 70" in prompt


def test_topic_reviewer_prompt_uses_the_configured_approval_threshold():
    candidate = SimpleNamespace(topic="Un sujet.")

    prompt = build_topic_reviewer_prompt(TARGET_WORDS, candidate, approval_threshold=80)

    assert "score >= 80" in prompt


# TC13: wrap-up


def test_wrap_up_lists_every_correction_and_both_word_lists():
    session = make_session()
    first = Correction(
        original="j'ai mange", corrected="j'ai mangé", explanation="Accent aigu."
    )
    second = Correction(
        original="des pomme", corrected="des pommes", explanation="Accord du nom."
    )
    session.turns.append(
        DialogTurn(
            role=DialogRole.LEARNER,
            text="J'ai mange des pomme.",
            target_words_used=["canicule"],
        )
    )
    session.turns.append(
        DialogTurn(role=DialogRole.SYSTEM, text="Bien !", corrections=[first])
    )
    session.turns.append(
        DialogTurn(role=DialogRole.LEARNER, text="Il fait chaud.", target_words_used=[])
    )
    session.turns.append(
        DialogTurn(role=DialogRole.SYSTEM, text="Oui !", corrections=[second])
    )

    wrap_up = build_wrap_up(session)

    assert "Bravo, la conversation est terminée !" in wrap_up
    assert "Mots utilisés : canicule" in wrap_up
    assert "Mots à revoir : sécheresse, prévenir, chaleur" in wrap_up
    assert "- « j'ai mange » → « j'ai mangé » : Accent aigu." in wrap_up
    assert "- « des pomme » → « des pommes » : Accord du nom." in wrap_up


def test_wrap_up_handles_empty_lists():
    wrap_up = build_wrap_up(make_session())

    assert "Mots utilisés : aucun" in wrap_up
    assert f"Mots à revoir : {', '.join(TARGET_WORDS)}" in wrap_up
    assert "Corrections : aucune" in wrap_up


# Markers: each appears in exactly its own prompt, so the mock cannot drift


def test_markers_appear_in_exactly_their_own_prompt():
    session = make_session()
    prompts = {
        TURN_CREATOR_MARKER: build_creator_prompt(session, "Salut", is_closing=False),
        TURN_REVIEWER_MARKER: build_reviewer_prompt(
            session, "Salut", turn_candidate(), is_closing=False
        ),
        TOPIC_CREATOR_MARKER: build_topic_creator_prompt(TARGET_WORDS),
        TOPIC_REVIEWER_MARKER: build_topic_reviewer_prompt(
            TARGET_WORDS, SimpleNamespace(topic="Un sujet.")
        ),
    }

    for marker, own_prompt in prompts.items():
        assert marker in own_prompt
        for other_marker, other_prompt in prompts.items():
            if other_marker != marker:
                assert marker not in other_prompt


# Mock LLM answers for the four dialog prompts


def test_mock_returns_valid_json_for_each_dialog_prompt():
    session = make_session()
    prompts = {
        "turn_creator": build_creator_prompt(session, "Salut", is_closing=False),
        "turn_reviewer": build_reviewer_prompt(
            session, "Salut", turn_candidate(), is_closing=False
        ),
        "topic_creator": build_topic_creator_prompt(TARGET_WORDS),
        "topic_reviewer": build_topic_reviewer_prompt(
            TARGET_WORDS, SimpleNamespace(topic="Un sujet.")
        ),
    }
    mock = MockLLMClient()

    for name, prompt in prompts.items():
        payload = json.loads(mock.generate(prompt))
        if name.endswith("reviewer"):
            verdict = ReviewVerdict.model_validate(payload)
            assert verdict.approved is True
            assert verdict.score >= 70
        elif name == "topic_creator":
            assert payload["topic"]
        else:
            assert payload["reply"]
            assert payload["corrections"] == []
            assert payload["target_words_used"] == []


def test_mock_reviewer_verdict_is_overridable_via_responses():
    rejection = '{"approved": false, "score": 10, "feedback": "Non."}'
    mock = MockLLMClient(responses={TURN_REVIEWER_MARKER: rejection})
    prompt = build_reviewer_prompt(
        make_session(), "Salut", turn_candidate(), is_closing=False
    )

    assert mock.generate(prompt) == rejection
    verdict = ReviewVerdict.model_validate(json.loads(rejection))
    assert verdict.approved is False


def test_mock_topic_reviewer_verdict_is_overridable_via_responses():
    rejection = '{"approved": false, "score": 0, "feedback": "Hors sujet."}'
    mock = MockLLMClient(responses={TOPIC_REVIEWER_MARKER: rejection})
    prompt = build_topic_reviewer_prompt(
        TARGET_WORDS, SimpleNamespace(topic="Un sujet.")
    )

    assert mock.generate(prompt) == rejection


def test_mock_responses_override_does_not_leak_into_other_prompts():
    mock = MockLLMClient(responses={TURN_REVIEWER_MARKER: "override"})

    topic_prompt = build_topic_creator_prompt(TARGET_WORDS)

    assert mock.generate(topic_prompt) != "override"


# Template files and rendering


def test_prompt_templates_are_loaded_from_txt_files():
    for name, marker_placeholder in [
        ("turn_creator", "{TURN_CREATOR_MARKER}"),
        ("turn_reviewer", "{TURN_REVIEWER_MARKER}"),
        ("topic_creator", "{TOPIC_CREATOR_MARKER}"),
        ("topic_reviewer", "{TOPIC_REVIEWER_MARKER}"),
    ]:
        template = _load_template(name)
        assert marker_placeholder in template


def test_render_replaces_inline_placeholders_and_leaves_unknown_ones():
    assert _render("A {x} B {inconnu}", {"x": "1"}) == "A 1 B {inconnu}"


def test_render_block_placeholder_is_replaced_by_its_lines_or_dropped():
    template = "Début\n{block}\n\nFin"

    assert _render(template, {"block": ["Un.", "Deux."]}) == "Début\nUn.\nDeux.\n\nFin"
    assert _render(template, {"block": []}) == "Début\n\nFin"


def test_render_does_not_rescan_replaced_values():
    assert _render("{history}", {"history": "{x}", "x": "1"}) == "{x}"
