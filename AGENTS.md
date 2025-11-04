# Repository Guidelines
必须中文回复和思考
## Project Structure & Module Organization
- `kode/` holds production Python packages: `agents/` for prompt chaining, `core/` for runtime, `services/` for integrations, `tools/` for task-specific utilities, and `web/` for FastAPI helpers.
- `tests/` mirrors the runtime modules with `test_*.py` suites.
- `examples/` contains runnable workflows illustrating agent setups.
- `web-frontend/` hosts the React client; coordinate API schema changes with this UI.
- `.env` and `.kode.json` control local credentials; base new configs on the corresponding `.example` files.

## Build, Test & Development Commands
- `poetry install` - set up the virtualenv using Poetry (Python 3.10).
- `poetry run kode --help` - inspect the CLI entrypoints in `kode.cli.main`.
- `poetry run kode-web` or `./start-web.sh` - launch the FastAPI backend with websocket support.
- `poetry run pytest` - execute the full unit test suite with pytest and asyncio auto mode.
- `poetry run ruff check .` / `poetry run black .` - run the linters before pushing.

## Coding Style & Naming Conventions
- Follow Black defaults with 4-space indentation and a 100-char line width; avoid trailing whitespace.
- Let Ruff (`E,F,I,N,W`) and MyPy (`disallow_untyped_defs = true`) guide imports, nullability, and typing; new functions should be fully annotated.
- Name modules and files in snake_case; use PascalCase for classes and descriptive verb phrases for CLIs and services.

## Testing Guidelines
- Co-locate tests under `tests/` using `test_<module>.py` naming; mirror fixtures per feature.
- Use `pytest.mark.asyncio` for async boundaries and prefer dependency injection over patching globals.
- Update or generate seed datasets in `kode.db` via dedicated fixtures; do not commit mutated databases.

## Commit & Pull Request Guidelines
- Write imperative, <=72 character summaries (e.g., `Add agent registry bootstrap`); add context in the body when behavior changes or migrations run.
- Reference issues with `Closes #123` and list validation commands executed.
- PRs should include a short change log, screenshots or GIFs for UI updates, and notes on schema or config impacts.
