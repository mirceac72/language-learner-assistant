# Language Learner Assistant - Roadmap

## Overview

This document outlines the development priorities, milestones, and success metrics for the Language Learner Assistant project.

---

## Current Status

**Version**: 0.1.0
**Status**: Core functionality implemented (vocabulary extraction, exercise generation, agent workflow)
**Specs Directory**: Newly created - existing features need formal specifications

---

## Priority Levels

| Priority | Icon | Description | Timeline |
|----------|------|-------------|----------|
| High | 🔴 | Critical for core functionality, must be addressed immediately | Current sprint |
| Medium | 🟡 | Important improvements, should be addressed soon | Next 1-2 sprints |
| Low | 🟢 | Nice-to-have, enhancement features | Future consideration |

---

## Development Priorities

### High Priority (Do First)

1. **Create specifications for existing features**
   - Vocabulary extraction pipeline spec
   - Exercise generation spec (includes agent workflow)
   - Answer evaluation spec
   - UI/UX workflow specs:
     - UI Creation phase spec (URL input → vocabulary extraction → exercise generation)
     - UI Practice phase spec (exercise display → answer input → submission)
     - UI Review phase spec (feedback display → continue → completion)

   **Implementation Plan**:
   
   | # | Specification | Files to Reference | Dependencies |
   |---|---------------|-------------------|--------------|
   | 1 | `feat-vocabulary-extraction-spec.md` | `web/vocabulary_extractor.py`, `web/ner_filter.py` | None |
   | 2 | `feat-exercise-generation-spec.md` | `exercises/generator.py`, `exercises/agents/*`, `models/exercise.py` | Vocabulary extraction |
   | 3 | `feat-answer-evaluation-spec.md` | `evaluation/evaluator.py` | Exercise generation |
   | 4 | `feat-ui-creation-phase-spec.md` | `app.py`, `run_streamlit.py`, `ui/vocabulary_display.py` | Vocabulary extraction, Exercise generation |
   | 5 | `feat-ui-practice-phase-spec.md` | `app.py`, `ui/exercise_display.py`, `exercises/player.py` | Answer evaluation |
   | 6 | `feat-ui-review-phase-spec.md` | `ui/exercise_display.py`, `exercises/player.py` | Practice phase |
   
   **Steps**: Analyze code → Create draft specs → Link specs → Review → Finalize
   
   **Estimated Effort**: 8-12 hours total
   
2. **Formalize quality standards**
   - Exercise review criteria and scoring thresholds
   - Code review checklists
   - Testing requirements for each component

3. **Complete core feature set**
   - Implement all exercise types (sentence construction currently limited)
   - Enhance answer evaluation with LLM-based feedback
   - Add exercise difficulty level support

4. **Exercise management**
   - Session persistence (save/load progress)
   - Exercise difficulty adaptation based on user performance
   - Exercise history and review mode

5. **Three-phase user workflow**
   - Implement Creation phase: URL input to exercise generation and local save
   - Implement Practice phase: loading and completing saved exercises
   - Implement Review phase: viewing past sessions and performance metrics

### Medium Priority (Do Next)

1. **Multi-language support**
   - Spec for language-agnostic architecture
   - Implement configuration for different languages
   - Add support for Dutch

2. **Configuration & Settings**
   - User-accessible configuration UI
   - Preset configurations for different learning levels
   - Export/import configuration profiles

3. **Enhanced vocabulary processing**
   - Part-of-speech tagging for better filtering
   - Lemmatization support
   - Custom stopword lists

### Low Priority (Nice to Have)

1. **Performance optimization**
   - Caching for vocabulary extraction results
   - Batch processing for exercise generation
   - Async operations for better responsiveness

2. **Error handling & resilience**
   - Comprehensive error messages for users
   - Retry logic with exponential backoff
   - Graceful degradation when services are unavailable

3. **Monitoring & Analytics**
   - Usage analytics (opt-in)
   - Performance metrics collection
   - Error reporting and logging

4. **Security enhancements**
   - API key rotation support
   - Rate limiting for LLM calls
   - Input validation and sanitization

---

## Success Metrics

### Product Metrics

| Metric | Target | Current | Measurement |
|--------|--------|---------|-------------|
| Vocabulary extraction accuracy | >= 90% | TBD | % of meaningful words captured |
| Exercise approval rate | >= 70% | TBD | % of generated exercises passing review |
| User answer evaluation accuracy | >= 95% | TBD | % of correct identifications |
| Session completion rate | >= 80% | TBD | % of started sessions finished |

### Technical Metrics

| Metric | Target | Current | Measurement |
|--------|--------|---------|-------------|
| Test coverage | >= 80% | TBD | % of code paths covered |
| Lint compliance | 100% | TBD | ruff check pass rate |

---

## Milestones

### Milestone 1: High Priority Features
**Goal**: Implement all high-priority features from the roadmap

- [ ] Create specifications for existing features
- [ ] Formalize quality standards
- [ ] Complete core feature set
- [ ] Exercise management
- [ ] Three-phase user workflow

### Milestone 2: Core Quality
**Goal**: Ensure quality standards and complete core functionality

- [ ] All specs reviewed and approved
- [ ] Test coverage >= 80%
- [ ] All high-priority bugs fixed
- [ ] Documentation complete

### Milestone 3: Medium Priority Features
**Goal**: Implement medium-priority features from the roadmap

- [ ] Multi-language support
- [ ] Configuration & Settings
- [ ] Enhanced vocabulary processing

### Milestone 4: Low Priority Features
**Goal**: Implement low-priority features from the roadmap

- [ ] Performance optimization
- [ ] Error handling & resilience
- [ ] Monitoring & Analytics
- [ ] Security enhancements

---

## Open Questions

These questions need to be resolved before implementing certain features:

### Architecture Questions

1. **Session Persistence**: Should we support saving progress between sessions?
   - If yes, what storage backend? (local file, database, cloud)
   - Should sessions be tied to users?
   
2. **Multi-Language Architecture**: How should we structure language-specific components?
   - Separate modules per language?
   - Configuration-driven with language parameters?
   - Plugin architecture?

3. **LLM Provider Abstraction**: Should we support multiple LLM providers beyond Mistral?
   - If yes, what interface should we design?
   - Should it be configurable per-session or per-application?

### Feature Questions

4. **Exercise Types**: Should we add more exercise types?
   - Listening comprehension?
   - Speaking practice?
   - Grammar exercises?
   - Dialogue practice?

5. **Spaced Repetition**: Should we implement a spaced repetition system?
   - If yes, what algorithm? (Anki-style, Leitner system, etc.)
   - Should it integrate with session persistence?

6. **Vocabulary Enhancements**: Should we add word hints or definitions?
   - Display word definitions from a dictionary API?
   - Show word frequency in source language?
   - Provide example sentences?

7. **Gamification**: Should we add gamification elements?
   - Streaks?
   - Achievements?
   - Leaderboards?

### Technical Questions

8. **Testing Strategy**: How should we test LLM-dependent features?
   - More comprehensive mock testing?
   - Integration tests with test API keys?
   - Property-based testing?

9. **Performance**: What performance targets are acceptable?
   - Maximum acceptable latency for exercise generation?
   - Vocabulary extraction from very large pages?

10. **Dependencies**: Are there any dependency constraints we should consider?
    - Maximum number of dependencies?
    - Dependency size limits?
    - Licensing restrictions beyond Apache 2.0?

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | TBD | Initial roadmap document created |
