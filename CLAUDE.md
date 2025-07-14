# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a local RAG-powered bookmark intelligence system built with Python. It uses Ollama (local LLM) and ChromaDB (vector database) to enrich bookmark collections with AI-generated descriptions and tags, then provides semantic search capabilities. The system processes JSON bookmark files and maintains consistency by using existing enriched bookmarks as RAG context.

## Key Commands

### Environment Setup
```bash
# Create virtual environment 
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (for testing)
pip install -r requirements-dev.txt
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=util/shared --cov-report=html

# Run specific test file
pytest util/tests/test_models.py

# Run only fast tests (exclude slow integration tests)
pytest -m "not slow"
```

### Code Quality
```bash
# Format code
black util/

# Check style
flake8 util/

# Type checking
mypy util/
```

### Ollama Setup (Required for Enrichment)
```bash
# Start Ollama service
ollama serve

# Pull required models
ollama pull nomic-embed-text
ollama pull llama3.1:8b

# Check if models are installed
ollama list
```

### Bookmark Enrichment
```bash
# Enrich single file
python util/bookmark_enricher.py bookmarks.json

# Enrich all JSON files in directory
python util/bookmark_enricher.py json/ --directory

# Use custom models
python util/bookmark_enricher.py json/ --embedding-model mxbai-embed-large --llm-model mistral:7b
```

## Architecture

### Core Components (`util/shared/`)

- **models.py**: Data models and validation
  - `Bookmark`: Main bookmark data structure with flexible JSON field support
  - `is_valid_url()`: URL validation function
  - `SimilarBookmark`, `SearchResult`, `DuplicateGroup`: Search/analysis result models

- **bookmark_loader.py**: File I/O operations
  - `BookmarkLoader`: Handles loading/saving JSON files and directories
  - Supports both single files and batch directory processing
  - Maintains source file metadata for proper saving

- **vector_store.py**: ChromaDB integration
  - `VectorStore`: Manages embedding storage and semantic search
  - Uses Ollama for generating embeddings
  - Handles bookmark indexing and similarity search

- **web_extractor.py**: Web content extraction
  - `WebExtractor`: Extracts title/description from URLs
  - Handles various HTML parsing scenarios
  - Includes timeout and error handling

### Main Tools

- **bookmark_enricher.py**: Primary enrichment tool
  - `BookmarkEnricher`: Orchestrates the RAG-based enrichment process
  - Uses existing enriched bookmarks as context for new enrichments
  - Generates descriptions and tags using local LLM
  - Includes comprehensive error tracking and reporting

### Data Flow

1. **Load**: BookmarkLoader reads JSON files into Bookmark objects
2. **Index**: Existing enriched bookmarks are indexed in ChromaDB vector store
3. **Enrich**: For each unenriched bookmark:
   - Extract web content if missing
   - Find similar bookmarks via vector search
   - Generate enrichment using LLM with RAG context
   - Update bookmark with description and tags
4. **Save**: BookmarkLoader saves enriched bookmarks back to original files

## Bookmark JSON Format

The system supports flexible bookmark formats with these mappings:
- URL: `url` or `link`
- Description: `description` or `excerpt`
- Tags: `tags` (array)
- Type: `type` (defaults to "link")

```json
[
  {
    "url": "https://example.com",
    "title": "Example Site",
    "description": "Site description",
    "tags": ["tag1", "tag2"],
    "type": "link"
  }
]
```

## Testing Structure

Tests are located in `util/tests/` with pytest configuration in `pytest.ini`:
- `test_models.py`: Data model validation tests
- `test_bookmark_loader.py`: File I/O operation tests
- `test_web_extractor.py`: Web scraping functionality tests
- `test_vector_store.py`: Vector database operation tests
- `conftest.py`: Shared test fixtures and configuration

Tests use markers:
- `slow`: Integration tests that can be skipped with `-m "not slow"`
- `integration`: Full system integration tests
- `unit`: Isolated unit tests

## Dependencies

**Production** (requirements.txt):
- `requests`: HTTP client for web scraping
- `beautifulsoup4`: HTML parsing
- `chromadb`: Vector database
- `ollama`: Local LLM API client
- `lxml`: XML/HTML parser

**Development** (requirements-dev.txt):
- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting
- `black`: Code formatting
- `flake8`: Style checking
- `mypy`: Type checking

## Common Issues

1. **lxml installation fails**: Use `arch -arm64 pip install lxml --no-cache-dir` on M1/M2/M3 Macs
2. **Ollama connection refused**: Ensure `ollama serve` is running
3. **Out of memory**: Use smaller models or process in smaller batches
4. **Missing models**: Run `ollama pull nomic-embed-text` and `ollama pull llama3.1:8b`

## Development Notes

- The system is designed to be 100% local and privacy-focused
- All AI processing happens on-device via Ollama
- ChromaDB provides persistent vector storage
- Web extraction includes respectful delays and error handling
- The enrichment process is fault-tolerant with comprehensive error reporting