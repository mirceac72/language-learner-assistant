# Plan: dialog practice

**Status**: Review
**Intent**: `../intent/dialog-practice-intent.md`
**Spec**: `../specs/feat-dialog-practice-spec.md` (Approved)
**Stage**: 3 - Build (AI-native SDLC playbook). Next artifact: the diff and its tests, one commit per step below

---

## Scope

Everything in the spec's eight implementation steps, reordered so that each step ends with
passing tests and a commit. Out of scope: Step 5 of the vocabulary extraction spec (text
and data mining opt-out), migrating `ExerciseWorkflow` to the generic review loop, disk
persistence of completed dialogs, external prompt files.

## Files that change

### New

| File | Contents |
|------|----------|
| `src/language_learner/core/review_loop.py` | `ReviewVerdict`, `Creator`/`Reviewer` protocols, `ReviewLoopResult`, `ReviewLoopWorkflow` (LangGraph) |
| `src/language_learner/models/dialog.py` | `DialogRole`, `DialogStatus`, `Correction`, `DialogTurn`, `DialogSession`, `DialogSummary` |
| `src/language_learner/dialogs/__init__.py` | package marker |
| `src/language_learner/dialogs/dialog_prompts.py` | `LEARNER_LEVEL`, prompt marker constants, four French prompt builders (load and render the templates), `build_wrap_up` |
| `src/language_learner/dialogs/prompts/*.txt` | the four LLM prompt templates (`turn_creator.txt`, `turn_reviewer.txt`, `topic_creator.txt`, `topic_reviewer.txt`) with `{placeholder}` markers |
| `src/language_learner/dialogs/agents/__init__.py` | package marker |
| `src/language_learner/dialogs/agents/dialog_turn_creator.py` | `DialogTurnContext` (with `carried_corrections`), `CorrectionOutput`, `DialogTurnOutput`, `DialogTurnCreatorAgent`, parse-step filtering |
| `src/language_learner/dialogs/agents/dialog_turn_reviewer.py` | hard-failure short-circuit (empty or overlong reply), `DialogTurnReviewerAgent` |
| `src/language_learner/dialogs/agents/dialog_topic_creator.py` | `DialogTopicOutput`, `DialogTopicCreatorAgent` |
| `src/language_learner/dialogs/agents/dialog_topic_reviewer.py` | `DialogTopicReviewerAgent` |
| `src/language_learner/dialogs/dialog_player.py` | `DialogPlayer` |
| `src/language_learner/ui/dialog_display.py` | `display_dialog` |
| `tests/test_review_loop.py` | TC7, TC8, TC9, approval threshold (default and custom), exception propagation; stub creator/reviewer, no LLM |
| `tests/test_dialog_models.py` | TC1 |
| `tests/test_dialog_prompts.py` | TC2, TC13, TC16, TC21 |
| `tests/test_dialog_turn_creator.py` | TC3, JSON parsing, improve-on-feedback prompt content, TC4, TC5, TC6, TC20 (parse-step filtering: word normalisation and membership, correction rules) |
| `tests/test_dialog_turn_reviewer.py` | hard-failure short-circuit (empty or overlong reply, no LLM call) |
| `tests/test_dialog_topic_agents.py` | topic creator and reviewer with mock, TC15, TC17 |
| `tests/test_dialog_player.py` | TC10, TC11, TC12, TC19, full mock dialog (AC1), end by turn count, end by words used, end on reviewer exhaustion |
| `tests/test_dialog_display.py` | full dialog content check in the style of `test_streamlit_display.py` |
| `tests/integration/test_dialog_practice_integration.py` | TC14 (AC3, AC4, AC5, AC14), TC18; marked `integration` |

### Modified

| File | Change |
|------|--------|
| `src/language_learner/config.py` | `dialog_practice_enabled`, `dialog_words_per_dialog`, `dialog_max_learner_turns`, `dialog_max_turn_attempts` |
| `src/language_learner/exceptions.py` | `DialogTurnError(LLMError)` |
| `src/language_learner/core/mock_llm.py` | recognise the four dialog prompt markers, return valid JSON; reviewer verdict overridable through `responses` |
| `src/language_learner/core/application.py` | build turn and topic loops; `create_dialog_topic`, `start_dialog_session` |
| `app.py` | practice-mode radio when enabled; `dialog_player`, `completed_dialogs`, `dialog_words_practised` in session state |
| `INSTRUCTIONS.md`, `README.md` | new settings, how to use dialog practice |
| `specs/tech-stack.md` | config table rows, `dialogs` module in the module list |
| `specs/mission.md` | dialog practice in the In Scope list |
| `specs/roadmap.md` | Feature Question 4 marked decided, pointing to the spec |
| `specs/feat-ui-review-phase-spec.md` | note that `completed_dialogs` is available for display |
| `specs/feat-dialog-practice-spec.md` | tick implementation steps and acceptance criteria as they land |

## Order of work

Each step ends with `uv run -m pytest tests/ -m "not integration"` and `uv run ruff check .`
green, then one commit with a single-line Conventional Commits message.

1. **Generic review loop.** `core/review_loop.py` and `tests/test_review_loop.py`. Pure
   Python stubs as creator and reviewer; no dialog code yet. Proves the loop, the feedback
   hand-off, the configurable approval threshold and the end-without-approval outcome in isolation.
   Commit: `feat: add generic creator/reviewer loop with feedback and end on exhaustion`

2. **Models, configuration, exception.** `models/dialog.py`, the four settings, `DialogTurnError`,
   `tests/test_dialog_models.py`.
   Commit: `feat: add dialog session models and dialog practice settings`

3. **Prompts and mock markers.** The four prompt templates live in `dialogs/prompts/*.txt`;
   `dialogs/dialog_prompts.py` loads them and renders them with placeholder replacement, with
   marker constants that both the builders and `MockLLMClient` import, so they cannot drift.
   The four prompts are written in French (structured-output field names stay English); this
   reduces the English content in the prompt and the risk of English leaking into learner-facing
   text. The creator prompt states that target words are returned exactly as listed; the closing
   prompt carries the discarded reply's correction. Extend `mock_llm.py` to answer all four
   prompts with valid JSON. `tests/test_dialog_prompts.py`.
   Commit: `feat: add dialog prompt builders and mock LLM responses for dialog practice`

4. **Turn agents.** `dialog_turn_creator.py`, `dialog_turn_reviewer.py`, their tests. The
   creator filters the parsed output (word normalisation and membership, correction rules);
   the reviewer only short-circuits on an empty or overlong reply before the LLM call and
   does not score `target_words_used`. First point where a real Mistral call is worth one
   manual run, to confirm the nested `CorrectionOutput` list survives strict `json_schema`
   mode (see Risks).
   Commit: `feat: add dialog turn creator and reviewer agents with structured output`

5. **Topic agents.** `dialog_topic_creator.py`, `dialog_topic_reviewer.py`,
   `tests/test_dialog_topic_agents.py`.
   Commit: `feat: add fictional dialog topic creator and reviewer agents`

6. **Player and application.** `dialogs/dialog_player.py`, `application.py` changes,
   `tests/test_dialog_player.py` including the full mock dialog (AC1). The last learner
   turn runs with `is_closing=True` directly; when the words run out earlier, the reply
   text is discarded, its corrections are carried into a closing loop run, and the closing
   turn is skipped when that loop fails. `start_dialog_session(vocabulary_words,
   practised_words)` selects the unpractised target words.
   Commit: `feat: add dialog player and wire dialog sessions into the application`

7. **UI.** `ui/dialog_display.py`, `app.py` wiring, `tests/test_dialog_display.py`. Manual
   run of the app with the mock client (no API key) to check rerun behaviour of
   `st.chat_input`.
   Commit: `feat: add dialog practice chat UI and practice-mode selector`

8. **Integration and manual validation.** `tests/integration/test_dialog_practice_integration.py`,
   then the manual test list from the spec with the real client. Fix prompts as needed;
   prompt changes here are expected.
   Commit: `test: add dialog practice integration tests and prompt adjustments`

9. **Documentation and spec closure.** Doc updates listed above; tick the spec's steps and
   acceptance criteria that are met, leave unmet ones unticked with a note.
   Commit: `docs: document dialog practice and close the spec implementation plan`

Steps 1, 2 and 3 are independent of each other and can be done in any order. Steps 4 and 5
both need 1 to 3. Step 6 needs 4 and 5. Everything else is sequential.

## Risks

| Risk | Where it bites | Handling |
|------|----------------|----------|
| Mistral strict `json_schema` rejects a nested object list (`corrections: list[CorrectionOutput]`), which produces `$defs` and `$ref` in the pydantic schema | Step 4 | Try one real call as soon as the creator exists. If rejected, inline the nested schema by hand or switch that call to `json_object` mode and validate with pydantic afterwards. Keep the `LLMClient` interface unchanged either way |
| `TypedDict` with `Generic` for the loop state, or dataclass instances inside LangGraph state | Step 1 | Python 3.12 supports generic TypedDict. If LangGraph copies state in a way that breaks dataclasses, keep the state as plain dicts and convert at the loop boundary |
| `st.chat_input` triggers a rerun before the turn is stored, losing the in-flight message | Step 7 | Append the learner turn and run the loop inside the same script run, before any rerun; store the player in `st.session_state`; remove the learner turn on failure as the spec requires |
| Mock responses drift from real prompt wording | Steps 3 to 8 | Marker constants shared between prompt builders and the mock; TC16 checks the builders contain them |
| Wrong corrections from `mistral-small` | Step 8 | Reviewer scores 0 on a wrong correction; if AC3 or AC4 fail repeatedly, tighten the correction rules in the creator prompt before considering a larger model |
| Dialog ends early when the reviewer rejects on every attempt of one turn | Step 8 | Wrap-up still shows progress; unpractised words stay available for the next dialog; exhaustion logged as a warning |
| Turn latency above 10 s with the 0.8 calls/s rate limit | Step 8 | Measure; lower `max_tokens`; if still slow, note in the spec's AC11 as not met rather than silently relaxing it |
| Ruff `UP` rules on `Protocol[C]` and `Generic[C]` syntax | Step 1 | Run ruff at the end of step 1; use the 3.12 syntax ruff prefers |

## Proof

- Unit suite green without an API key: `uv run -m pytest tests/ -v -m "not integration"`
- Integration suite green with a key: `uv run -m pytest tests/integration/ -v -m integration`
- Lint and format clean: `uv run ruff check .` and `uv run ruff format --check .`
- Existing exercise tests untouched and passing (AC8)
- Spec acceptance criteria AC1 to AC13 each ticked in the spec with the test or manual step
  that proves it; AC11 and AC12 are manual and recorded as measured
- Manual run through the six manual test scenarios in the spec, with the mock client for
  the UI checks and the real client for correction quality
