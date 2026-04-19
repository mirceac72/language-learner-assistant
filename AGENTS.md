# Instructions for agents

## Spec Driven Development

### Before Starting Work
Read the specification documents in the `specs` folder:
- `mission.md` - Mission statement, scope, and development workflow
- `roadmap.md` - Feature priorities and timeline
- Relevant feature specification documents (e.g., `feat-*.md`)

Refer to `specs/tech-stack.md` for:
- Technical stack, architecture, and data flow diagrams
- Development tools and commands (uv, pytest, ruff)
- Dependency constraints and package selection guidelines

### Specification Requirements
All features must have an approved specification before implementation. A complete specification includes:
- Clear user stories and requirements
- Technical design with architecture diagrams
- API interfacess and data models
- Acceptance criteria
- Test cases (unit, integration, manual)
- Dependencies and constraints

### Implementation Workflow
1. **Read spec** - Review all relevant specification documents
2. **Validate spec** - Ensure spec is in "Approved" status, not "Draft"
3. **Implement** - Write code matching spec requirements
4. **Test** - Write tests defined in spec's Test Cases section
5. **Verify** - Confirm implementation meets all acceptance criteria
6. **Update** - Mark spec tasks as complete in implementation plan

### Specification Status Management
Specifications follow a lifecycle: **Draft → Review → Approved**
- **Draft**: Initial creation, incomplete sections
- **Review**: Ready for peer review, all sections complete
- **Approved**: Reviewed and accepted, ready for implementation

Update the status in the spec document header when transitioning between states.

## Designing and Planning

When designing solutions:
1. Generate three alternative options
2. Select the simplest solution that meets requirements
3. Review the selected solution and simplify further
4. Document the chosen approach and rationale in the spec

## Naming

Avoid generic names like `creator`, `reviewer`, or `workflow` for file names. Use specific names instead:
- `exercise_creator.py` instead of `creator.py`
- `exercise_reviewer.py` instead of `reviewer.py`
- `exercise_workflow.py` instead of `workflow.py`

## Summaries

When creating work summaries:
- Maximum 3 paragraphs
- First pass: Write summary, identify missing important work, remove filler
- Second pass: Add any remaining important work, remove more filler
- Final pass: Verify completeness and conciseness
