# Intent: dialog practice for vocabulary from a page

**Status**: draft (open questions resolved, ready to commit)
**Stage**: 1 - Plan (AI-native SDLC playbook). Next artifact: `specs/feat-dialog-practice-spec.md`

---

## Problem

Today a learner gives the app a URL (a newspaper article, a Wikipedia page), the app
extracts a set of vocabulary words from the page and generates exercises for them
(fill-in-the-blank, multiple choice, translation, sentence construction, word matching).

This works, but every exercise is a closed question with one expected answer. The learner
never has to *use* the words to say something of their own. That is the gap between
recognising a word and being able to produce it in conversation, which is exactly what
an A2-B1 learner needs to practise.

What the learner cannot do today:

- Practise the words from the page in a free, conversational exchange with the system.
- Get their own sentences corrected while they are talking, instead of being graded
  against a single pre-written answer.
- Be gently pushed to reuse the target words in context over several turns.

## Proposed outcome

A new type of practice, **dialog practice**, alongside the existing exercises.

- The learner and the system hold a **short, open-form dialog in French** in a fictional
  everyday situation invented so that the words from the page come up naturally. The page
  itself is not retold. The learner types free text; the system replies in free text.
- The dialog is built around the **vocabulary extracted from the page**. The system steers
  the conversation so that the target words come up naturally and invites the learner to
  use them (asks questions that call for them, offers them when the learner is stuck).
- The system speaks at the **learner's level, A2 to B1** (CEFR): short sentences, common
  structures, high-frequency vocabulary apart from the target words, no idioms that an
  A2 learner would not know.
- **Mistakes are noticed and corrected inside the dialog.** When the learner's message
  contains an error (wrong word, gender, agreement, conjugation, word order, spelling
  that changes meaning), the system points it out briefly, shows the corrected form, and
  then continues the conversation. Corrections must not stop the flow or turn every turn
  into a grammar lesson: one or two corrections per turn, the most important ones first.
- Corrections are given **in French** (immersion), at the same A2-B1 level as the rest of
  the dialog.
- A dialog is **short**: 5 to 8 learner turns, built around 3 to 5 target words, ending
  earlier if all of them have been used. It ends with a brief wrap-up of which words were
  used and what was corrected. Several dialogs can be played from one page.
- The result of a dialog (words practised, corrections made) feeds the same progress
  record as the other exercise types, so the Review phase can show it.

### What better looks like

A learner at A2 pastes an article about a heat wave. The extracted words include
*canicule*, *sécheresse*, *prévenir*, *chaleur*. In dialog practice:

> **System**: Cette semaine il fait très chaud en France. Est-ce qu'il y a une canicule chez toi ?
> **Learner**: Oui, il fait beaucoup de chaleur. Le gouvernement prévient les gens pour boire de l'eau.
> **System**: Presque ! On dit « le gouvernement prévient les gens **de** boire de l'eau » (prévenir quelqu'un **de** faire quelque chose). Et il y a de la sécheresse dans ta région ?
> **Learner**: Oui, il n'y a pas de pluie depuis deux mois.
> **System**: Très bien, c'est une sécheresse. Qu'est-ce que tu fais pour éviter la chaleur ?

The learner has used *chaleur* and *prévenir*, been corrected once, and been led toward
*sécheresse* without leaving the conversation.

### Out of scope for this intent

- Audio or speech (text only, as in the mission document).
- Languages other than French.
- Multi-user or authenticated sessions.
- Assessing the learner's overall CEFR level. The level is an input (A2-B1), not
  something the dialog has to measure.

## Affected users and systems

**Users**

- French learners at A2-B1, the app's primary users. They get a new practice type.
- The developer maintaining the app: a new kind of interaction that is not a
  question/answer exercise, so the practice-phase UI, session model and evaluation
  need an extension rather than a new exercise type.

**Systems (current code and specs that this touches)**

- Practice phase UI (`app.py`, `ui/exercise_display.py`): needs a chat-style view in
  addition to the one-exercise-at-a-time view. See `specs/feat-ui-practice-phase-spec.md`.
- Session and progress model (`exercises/player.py`, `models/exercise.py`): a dialog is a
  multi-turn interaction, not an `Exercise` with one `correct_answer`. Progress recording
  has to accept dialog outcomes (words used, corrections).
- Evaluation (`evaluation/evaluator.py`): today evaluates one answer against one expected
  answer. Dialog needs in-turn error detection and correction with no expected answer.
  See `specs/feat-answer-evaluation-spec.md`.
- LLM layer (`core/llm_interface.py`, `core/llm_client.py`, `core/mock_llm.py`): the
  dialog needs conversation history in the prompt and structured output (reply +
  corrections). The mock client must be able to play a dialog so unit tests stay offline.
- Configuration (`config.py`): dialog practice should be switchable like the other
  exercise types (`EXERCISE_TYPES`), with a few tunables (turns per dialog, words per
  dialog).
- Review phase (`specs/feat-ui-review-phase-spec.md`): show dialog results next to
  exercise results.
- Roadmap: this answers Feature Question 4 in `specs/roadmap.md` ("Dialogue practice?")
  with a yes.

## Constraints

- Keep the current three-phase flow (Creation, Practice, Review). Dialog practice is one
  more option in Practice. It does not replace the existing exercises.
- Use the existing LLM abstraction (`LLMClient`, Mistral, rate limiter, retries). No new
  LLM provider and, preferably, no new dependencies.
- Streamlit stays the UI. Streamlit has a native chat widget, which should be enough.
- Runs locally, text only, French only, no user accounts (mission document scope).
- Dialog practice uses only the extracted words. No page text is sent to the LLM for it
  or stored.
- Publishers can reserve text and data mining rights in machine-readable form (robots.txt,
  the TDM Reservation Protocol, `noai`). A page that does so is refused and nothing from
  it is processed.
- Every system message must stay within A2-B1: short sentences, common vocabulary,
  present/passé composé/futur proche as the default tenses. The target words from the
  page are the exception and may be harder.
- Corrections must be correct. A wrong correction is worse than no correction. Every
  system turn (reply and corrections) goes through the creator/reviewer agent workflow
  before it is shown, as exercises do today. The spec must budget the extra latency per
  turn.
- The learner level is fixed at A2-B1 for now. It is a constant in the prompt, not a
  user setting.
- A dialog must be unit-testable with `MockLLMClient` and must have at least one
  integration test with the real Mistral client, as the other LLM features do.
- LLM cost and latency: each learner turn is at least two LLM calls (creator, then
  reviewer). Dialogs are short by design so that a full dialog stays in the same cost
  range as a set of exercises.

## Decisions

The spec must follow these.

1. **Correction language: French.** Immersion. Corrections and their short explanation
   are in French at A2-B1 level, no English fallback.
2. **Correction style: explicit for the main error, recast for the rest.** The most
   important error in a learner turn is corrected explicitly ("On dit X"), other errors
   are only reused in their correct form in the system's reply, so the dialog keeps
   moving.
3. **Dialog length: 5 to 8 learner turns**, or earlier once all target words of that
   dialog have been used.
4. **Words per dialog: 3 to 5**, taken from the top of the extracted list, so one page
   gives several dialogs.
5. **Learner stuck or off-topic**: accept the message (English, one word, off-topic),
   reply briefly at level, and ask a question that brings back the next target word.
6. **Quality review: every dialog turn goes through the creator/reviewer workflow**
   before display. Extra latency is accepted for v1.
7. **Recorded per dialog for the Review phase**: target words the learner used
   correctly, and the corrections made. How they are displayed is decided in the
   review-phase spec.
8. **Level: fixed at A2-B1.** No learner-facing level setting for now.
9. **Dialog topic: fictional, built from the target words, reviewed like a turn.** The
   model invents an everyday situation at A2-B1 in which the target words fit naturally
   and the reviewer checks it. The page is not summarised or retold.
10. **Generic review loop.** The create → review → improve → pick-best loop is built once
    as a reusable component, because the application will need it for every kind of
    generated content, not only dialog turns and topics.

## Open questions

None at this stage. New questions raised while writing the spec are carried forward
there.
