<!-- AI_AGENT_GUIDANCE: This file provides AI agents with instructions on interacting with this codebase. -->

# Introduction
This repository contains a local RAG powered bookmark intelligence system written in Python. It enriches bookmark collections with AI generated descriptions and tags using local models via Ollama and stores embeddings in ChromaDB. The system includes semantic search, duplicate detection, and intelligent import capabilities. This document is aimed at AI coding assistants and summarizes how the project is organized and how common development tasks are performed.

# Project Structure
- `bookmark_enricher.py` – command line tool that enriches bookmark files.
- `bookmark_intelligence.py` – semantic search and analysis tool.
- `bookmark_importer.py` – import bookmarks from various formats with automatic duplicate detection.
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
   python bookmark_intelligence.py json/ --create-category "3d-printing"  # create new category files
   python bookmark_intelligence.py json/ --populate-category "3d-printing"  # intelligently populate categories
   python bookmark_importer.py json/ new_bookmarks.json  # includes duplicate detection
   ```
4. Run tests and quality checks:
   ```bash
   pytest
   black .
   ruff check .
   mypy core/
   ```

# Key Features

## Duplicate Detection System
The bookmark importer includes a sophisticated multi-level duplicate detection system:

1. **URL Matching** (fastest): Exact URL comparison
2. **Title Matching** (fast): Normalized, case-insensitive title comparison  
3. **Content Similarity** (thorough): Semantic similarity using vector embeddings from the already-loaded ChromaDB index

The system is designed to be efficient by leveraging the existing `BookmarkIntelligence` instance that already has the vector database loaded. This means duplicate checking adds minimal overhead to the import process.

**Usage:**
```bash
# Default: includes duplicate detection
python bookmark_importer.py json/ new_bookmarks.json

# Skip duplicate checking for faster import
python bookmark_importer.py json/ new_bookmarks.json --no-duplicate-check
```

## Category Management System
The system includes comprehensive category management capabilities:

**Category Creation and Population**:
- `--create-category`: Creates empty category JSON files
- `--populate-category`: Uses semantic search to find bookmarks that belong in specific categories
- Interactive workflow with user approval for safe bookmark moving
- Gradual population approach (small batches, high confidence threshold)

**Core Module**: `core/category_manager.py` provides reusable category management functionality used by the CLI interface.

**Example Usage**:
```bash
# Create empty category
python bookmark_intelligence.py json/ --create-category "machine-learning"

# Populate with high-confidence matches (interactive)
python bookmark_intelligence.py json/ --populate-category "machine-learning"

# Customize parameters
python bookmark_intelligence.py json/ --populate-category "web-dev" --limit 10 --threshold 0.8
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
