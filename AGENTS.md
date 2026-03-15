# Instructions for agents

## Designing and planning

When making designing or making plans choose the simplest possible solutions. Generate three alternative options and select the simplest solution. Review the generated solution and make it simpler.

## Naming

Avoid names that are too generic like creator, reviewer or workflow for file names. Use instead exercise_creator, exercise_reviewer, exercise_workflow.

## Summaries

When creating summaries of your work, make a maximum 3 paragraphs summary, review the summary and the missing important work that is missing and remove the filler,
make a second final check and add any missing important work and remove the filler.

## Use uv to manage the Python environment

Do NOT use python directly in bash command lines. Use uv.

Useful uv commands are:
- `uv add/remove <package>` to manage dependencies
- `uv sync` to install dependencies declared in pyproject.toml and uv.lock
- `uv run script.py` to run a script within the uv environment
- `uv run -m pytest tests/ -v` to run pytest (or any other python tool) within the uv environment. Do NOT use `python -m pytest tests/ -v`to run the tests. 
- `uv run ruff check --fix` to run the ruff formating checks and automatically fix the issues

## Packages and dependecies

- Prefer standard Python packages
- Use as few as possible dependent packages
- Use only well established Python packages.
- Use only Python packages whose license is compatible with Apache 2.0 license of the application
