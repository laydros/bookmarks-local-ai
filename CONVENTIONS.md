# Project Conventions

This document describes the coding standards and workflow used in this repository. It is intended for both human contributors and AI coding assistants.

## Project Overview
The codebase implements a local bookmark enrichment and intelligence system. Python scripts interact with Ollama for local LLM models and use ChromaDB for embedding storage. Tests are written with `pytest` and tooling configuration lives in `pyproject.toml`.

## Development Environment
- **Python Version:** 3.8 or newer
- **Dependency Management:** `pyproject.toml` with optional `.[dev]` extras
- **Virtual Environment:** create with `python -m venv .venv`
- **Testing Framework:** `pytest`
- **Linting/Formatting:** `ruff`, `black`, and `mypy`

## Coding Standards
### Python Style
- Follow PEP 8 with 4‑space indentation
- Maximum line length is 88 characters
- Use type hints for all functions and dataclasses when possible
- Prefer f-strings for string formatting
- Organize imports: standard library, third‑party, then local

### Code Organization
- Core functionality lives in the `core/` package
- CLI entry points are in the repository root (`bookmark_enricher.py`, etc.)
- Tests reside in `tests/` mirroring the package structure
- Use dataclasses for structured data

### Error Handling
- Raise specific exception types; avoid bare `except:`
- Log errors with context using the standard `logging` module
- Validate inputs early and use context managers for file operations

### Documentation
- Provide docstrings for public functions and classes (Google style)
- Update `README.md` and other docs when behavior changes

### Testing
- Write tests for all new features or bug fixes
- Use descriptive test names and the Arrange‑Act‑Assert pattern
- Mock external services (e.g., network requests) in unit tests

## Git Workflow
- Create feature branches from `main`
- Use conventional commit messages: `type(scope): description`
- Keep commits small and focused
- Run `pytest` and linters before committing

## Common Patterns
- Use `pathlib.Path` for file paths
- Prefer `json.loads()` over `eval()`
- Use context managers for file and network operations
- Avoid global variables and commented‑out code

