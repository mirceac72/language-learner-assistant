"""Tests for the dialog turn creator agent. Stub and mock LLM, no API calls."""

import json
import unicodedata

import pytest

from language_learner.core.mock_llm import MockLLMClient
from language_learner.dialogs.agents.dialog_turn_creator import (
    CorrectionOutput,
    DialogTurnContext,
    DialogTurnCreatorAgent,
    DialogTurnOutput,
)
from language_learner.dialogs.dialog_prompts import TURN_CREATOR_MARKER
from language_learner.exceptions import DialogTurnError
from language_learner.models.dialog import Correction, DialogSession

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


def make_session(target_words: list[str] = TARGET_WORDS) -> DialogSession:
    return DialogSession(
        dialog_id="dlg-1",
        target_words=list(target_words),
        dialog_topic="Il fait très chaud en été.",
        max_learner_turns=6,
    )


def make_context(
    session: DialogSession,
    learner_message: str | None = "Oui, il fait chaud.",
    is_closing: bool = False,
    carried_corrections: list[Correction] | None = None,
) -> DialogTurnContext:
    return DialogTurnContext(
        session=session,
        learner_message=learner_message,
        is_closing=is_closing,
        carried_corrections=carried_corrections or [],
    )


def correction_json(
    original: str, corrected: str, explanation: str = "Explication."
) -> dict:
    return {"original": original, "corrected": corrected, "explanation": explanation}


def turn_json(
    reply: str = "Bien ! Et chez toi ?",
    corrections: list[dict] | None = None,
    target_words_used: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "reply": reply,
            "corrections": corrections or [],
            "target_words_used": target_words_used or [],
        },
        ensure_ascii=False,
    )


def create_with(response: str, context: DialogTurnContext) -> DialogTurnOutput:
    agent = DialogTurnCreatorAgent(StubLLM(response))
    return agent.create(context, None, None)


# JSON parsing and the LLM call


def test_create_parses_valid_json_and_uses_structured_output():
    session = make_session()
    context = make_context(session)
    stub = StubLLM(
        turn_json(
            reply="Bien !",
            corrections=[correction_json("il fait chaud", "il fait très chaud")],
            target_words_used=["chaleur"],
        )
    )

    output = DialogTurnCreatorAgent(stub).create(context, None, None)

    assert output.reply == "Bien !"
    assert output.corrections == [
        CorrectionOutput(
            original="il fait chaud",
            corrected="il fait très chaud",
            explanation="Explication.",
        )
    ]
    assert output.target_words_used == ["chaleur"]
    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert TURN_CREATOR_MARKER in call["prompt"]
    assert call["temperature"] == 0.7
    assert call["max_tokens"] == 300
    assert call["response_schema"] == DialogTurnOutput.model_json_schema()


def test_create_parses_json_wrapped_in_a_code_fence():
    context = make_context(make_session())

    output = create_with(f"```json\n{turn_json(reply='Salut !')}\n```", context)

    assert output.reply == "Salut !"


def test_create_with_mock_llm_client():
    context = make_context(make_session())

    output = DialogTurnCreatorAgent(MockLLMClient()).create(context, None, None)

    assert output.reply
    assert output.corrections == []
    assert output.target_words_used == []


# TC3: invalid LLM answers raise DialogTurnError


def test_create_raises_dialog_turn_error_on_non_json():
    context = make_context(make_session())

    with pytest.raises(DialogTurnError, match="non-JSON"):
        create_with("Ce n'est pas du JSON.", context)


def test_create_raises_dialog_turn_error_on_schema_mismatch():
    context = make_context(make_session())

    with pytest.raises(DialogTurnError, match="schema"):
        create_with('{"reply": "Salut !"}', context)


def test_create_raises_dialog_turn_error_on_extra_field():
    context = make_context(make_session())

    with pytest.raises(DialogTurnError, match="schema"):
        create_with(turn_json()[:-1] + ', "extra": 1}', context)


# TC4: a correction whose original is not in the learner message is dropped


def test_parse_step_drops_correction_whose_original_is_not_in_the_message():
    context = make_context(make_session(), learner_message="J'ai bu de l'eau.")

    output = create_with(
        turn_json(corrections=[correction_json("j'ai mangé", "j'ai mangé", "Faux.")]),
        context,
    )

    assert output.corrections == []


def test_parse_step_matches_original_case_insensitively():
    context = make_context(make_session(), learner_message="J'ai bu de l'eau.")

    output = create_with(
        turn_json(corrections=[correction_json("J'AI BU", "j'ai bu")]),
        context,
    )

    assert len(output.corrections) == 1
    assert output.corrections[0].original == "J'AI BU"


def test_parse_step_drops_correction_with_blank_original():
    context = make_context(make_session(), learner_message="J'ai bu de l'eau.")

    output = create_with(
        turn_json(corrections=[correction_json("   ", "j'ai bu")]),
        context,
    )

    assert output.corrections == []


# TC5: at most one correction is kept


def test_parse_step_keeps_only_the_first_of_two_corrections():
    context = make_context(
        make_session(), learner_message="J'ai bu et j'ai mangé une pomme."
    )

    output = create_with(
        turn_json(
            corrections=[
                correction_json("j'ai bu", "j'ai bu", "Première."),
                correction_json("une pomme", "des pommes", "Deuxième."),
            ]
        ),
        context,
    )

    assert len(output.corrections) == 1
    assert output.corrections[0].explanation == "Première."


# TC6: corrections on the opening and closing turns


def test_parse_step_drops_all_corrections_on_the_opening_turn():
    context = make_context(make_session(), learner_message=None, is_closing=False)

    output = create_with(
        turn_json(corrections=[correction_json("bonjour", "bonjour")]),
        context,
    )

    assert output.corrections == []


def test_parse_step_keeps_the_answered_messages_correction_on_a_closing_turn():
    context = make_context(
        make_session(), learner_message="J'ai bu de l'eau.", is_closing=True
    )

    output = create_with(
        turn_json(corrections=[correction_json("j'ai bu", "j'ai bu")]),
        context,
    )

    assert len(output.corrections) == 1


def test_parse_step_drops_all_corrections_on_a_closing_turn_carrying_a_correction():
    carried = Correction(
        original="j'ai bu", corrected="j'ai bu", explanation="Déjà montrée."
    )
    context = make_context(
        make_session(),
        learner_message="J'ai bu de l'eau.",
        is_closing=True,
        carried_corrections=[carried],
    )

    output = create_with(
        turn_json(corrections=[correction_json("j'ai bu", "j'ai bu")]),
        context,
    )

    assert output.corrections == []


# TC20: target-word normalisation and membership


def test_parse_step_normalises_proposed_target_words_and_keeps_listed_forms():
    session = make_session(target_words=["prévenir", "boire"])
    context = make_context(session)
    nfd_prevenir = unicodedata.normalize("NFD", "prévenir")

    output = create_with(
        turn_json(target_words_used=["prévient", "Boire", "bu", nfd_prevenir, "avion"]),
        context,
    )

    # "prévient" and "bu" are the learner's inflected forms, not listed
    # targets; "Boire" is normalised to the listed "boire"; the NFD form of
    # "prévenir" is normalised to NFC; "avion" is not a target at all.
    assert output.target_words_used == ["boire", "prévenir"]


def test_parse_step_drops_words_not_in_the_target_set():
    context = make_context(make_session())

    output = create_with(
        turn_json(target_words_used=["canicule", "avion", "sécheresse"]),
        context,
    )

    assert output.target_words_used == ["canicule", "sécheresse"]


# Retry attempts: the previous candidate and the feedback reach the prompt


def test_create_passes_previous_candidate_and_feedback_to_the_prompt():
    session = make_session()
    context = make_context(session)
    previous = DialogTurnOutput(
        reply="Ancienne réponse.",
        corrections=[
            CorrectionOutput(
                original="j'ai bu", corrected="j'ai bu", explanation="Accent."
            )
        ],
        target_words_used=["boire"],
    )
    stub = StubLLM(turn_json(reply="Réponse améliorée."))

    output = DialogTurnCreatorAgent(stub).create(context, previous, "Trop long.")

    assert output.reply == "Réponse améliorée."
    prompt = stub.calls[0]["prompt"]
    assert "Un relecteur a rejeté ta réponse précédente." in prompt
    assert "Réponse précédente : Ancienne réponse." in prompt
    assert "Commentaire du relecteur : Trop long." in prompt
    assert '"original": "j\'ai bu"' in prompt


def test_create_has_no_feedback_block_on_the_first_attempt():
    stub = StubLLM(turn_json())

    DialogTurnCreatorAgent(stub).create(make_context(make_session()), None, None)

    assert "Un relecteur" not in stub.calls[0]["prompt"]


def test_create_passes_carried_corrections_to_the_closing_prompt():
    carried = Correction(
        original="j'ai mange", corrected="j'ai mangé", explanation="Accent aigu."
    )
    context = make_context(
        make_session(),
        learner_message="J'ai mange une pomme.",
        is_closing=True,
        carried_corrections=[carried],
    )
    stub = StubLLM(turn_json(reply="Au revoir !"))

    DialogTurnCreatorAgent(stub).create(context, None, None)

    prompt = stub.calls[0]["prompt"]
    assert (
        "Correction à montrer d'abord : j'ai mange → j'ai mangé : Accent aigu."
        in prompt
    )
    assert "ce champ doit être une liste vide" in prompt


def test_create_leaves_the_reply_text_unfiltered():
    long_reply = " ".join(f"Phrase {i}." for i in range(1, 9))
    context = make_context(make_session())

    output = create_with(turn_json(reply=long_reply), context)

    assert output.reply == long_reply
