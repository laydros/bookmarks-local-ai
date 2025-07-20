<!-- AI_AGENT_GUIDANCE: This file provides AI agents with instructions on interacting with this codebase. -->

# Introduction
This repository contains a local RAG powered bookmark intelligence system written in Python. It enriches bookmark collections with AI generated descriptions and tags using local models via Ollama and stores embeddings in ChromaDB. This document is aimed at AI coding assistants and summarizes how the project is organized and how common development tasks are performed.

# Project Structure
- `bookmark_enricher.py` – command line tool that enriches bookmark files.
- `bookmark_intelligence.py` – semantic search and analysis tool.
- `bookmark_importer.py` – import bookmarks from various formats.
- `core/` – reusable modules such as models, bookmark loader, vector store and helpers.
- `tests/` – pytest suite covering the modules and command line tools.
- `default_config.txt` – example configuration values.
- `pyproject.toml` – dependencies and tool configuration.
- `CLAUDE.md` – extensive instructions for Claude.

# Build & Run
1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev]
   ```
2. Ensure Ollama is running and required models are pulled:
   ```bash
   ollama serve
   ollama pull nomic-embed-text
   ollama pull llama3.1:8b
   ```
3. Enrich bookmarks or run intelligence tools:
   ```bash
   python bookmark_enricher.py bookmarks.json
   python bookmark_intelligence.py json/ --search "python"
   ```
4. Run tests and quality checks:
   ```bash
   pytest
   black .
   ruff check .
   mypy core/
   ```

# Code Guidelines
- Follow [PEP 8](https://peps.python.org/pep-0008/) with 4‑space indentation.
- Line length is 88 characters and enforced by **black** and **ruff**.
- Type hints are required and checked with **mypy**.
- See [CONVENTIONS.md](CONVENTIONS.md) for detailed style and workflow rules.

# Contribution Workflow
1. Create a feature branch from `main`.
2. Make small, atomic commits using a conventional message style, e.g. `feat(core): add loader`.
3. Run tests and linters before committing.
4. Open a pull request describing the changes and reference relevant issues.

# Related Docs
- [README.md](README.md)
- [CONVENTIONS.md](CONVENTIONS.md)
- [CLAUDE.md](CLAUDE.md)
