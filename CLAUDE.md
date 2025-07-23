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

# Install dependencies (production + dev)
pip install -e .[dev]

# Or install just production dependencies
pip install -e .
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage (configured in pyproject.toml)
pytest --cov=core --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run only fast tests (exclude slow integration tests)
pytest -m "not slow"
```

### Code Quality
```bash
# Format code
black .

# Check style (using ruff)
ruff check .

# Type checking
mypy core/
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

### Bookmark Tools
```bash
# Enrich single file
python bookmark_enricher.py bookmarks.json
# Or use installed script
bookmark-enricher bookmarks.json

# Enrich all JSON files in directory
python bookmark_enricher.py json/ --directory

# Use custom models
python bookmark_enricher.py json/ --embedding-model mxbai-embed-large --llm-model mistral:7b

# Search and analyze bookmarks
python bookmark_intelligence.py search "machine learning"
# Or use installed script
bookmark-intelligence search "machine learning"

# Find duplicate bookmarks
python bookmark_intelligence.py duplicates bookmarks.json

# Suggest categories for bookmark organization
python bookmark_intelligence.py suggest-categories bookmarks.json

# Import bookmarks from browser exports
python bookmark_importer.py exported_bookmarks.html
# Or use installed script
bookmark-importer exported_bookmarks.html
```

## Architecture

### Core Components (`core/`)

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

- **config_manager.py**: Configuration management
  - `ModelConfig`, `ProcessingConfig`: Configuration dataclasses
  - Handles YAML/JSON config files and environment variables
  - Provides fallback model configurations

- **category_suggester.py**: AI-powered category suggestions
  - `CategorySuggester`: Analyzes bookmarks and suggests organizational categories
  - Uses HDBSCAN or K-means clustering for grouping similar bookmarks
  - Generates category names and descriptions using LLM

- **backup_manager.py**: Backup and restore functionality
  - Handles backup creation and restoration of bookmark files
  - Supports versioned backups with metadata

- **progress_tracker.py**: Progress tracking utilities
  - `ProgressTracker`: Thread-safe progress tracking for batch operations
  - Supports detailed logging and status reporting

- **spinner.py**: CLI spinner animations
  - Provides visual feedback for long-running operations

### Main Tools

- **bookmark_enricher.py**: Primary enrichment tool
  - `BookmarkEnricher`: Orchestrates the RAG-based enrichment process
  - Uses existing enriched bookmarks as context for new enrichments
  - Generates descriptions and tags using local LLM
  - Includes comprehensive error tracking and reporting

- **bookmark_intelligence.py**: Analysis and search tool
  - `BookmarkIntelligence`: Provides semantic search, duplicate detection, and analysis
  - Supports category suggestions and bookmark organization
  - Interactive search capabilities with similarity scoring

- **bookmark_importer.py**: Browser bookmark import tool
  - Imports bookmarks from various browser export formats
  - Handles HTML, JSON, and other bookmark export formats
  - Converts to standardized JSON format for processing

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

Tests are located in `tests/` with pytest configuration in `pyproject.toml`:
- `test_models.py`: Data model validation tests
- `test_bookmark_loader.py`: File I/O operation tests
- `test_web_extractor.py`: Web scraping functionality tests
- `test_vector_store.py`: Vector database operation tests
- `test_bookmark_intelligence.py`: Intelligence and search functionality tests
- `test_suggest_categories.py`: Category suggestion functionality tests
- `test_config.py`: Configuration management tests
- `conftest.py`: Shared test fixtures and configuration

Tests use markers:
- `slow`: Integration tests that can be skipped with `-m "not slow"`
- `integration`: Full system integration tests
- `unit`: Isolated unit tests

## Dependencies

**Production** (defined in pyproject.toml):
- `requests==2.32.4`: HTTP client for web scraping
- `beautifulsoup4==4.13.4`: HTML parsing
- `chromadb==1.0.15`: Vector database
- `ollama==0.5.1`: Local LLM API client
- `lxml`: XML/HTML parser
- `hdbscan==0.8.33`: Density-based clustering for category suggestions
- `scikit-learn==1.4.2`: Machine learning utilities
- `pydantic-settings==2.10.1`: Configuration management

**Development** (optional dependencies):
- `pytest==8.4.1`: Testing framework
- `pytest-cov==6.2.1`: Coverage reporting
- `pytest-mock==3.14.1`: Mocking utilities
- `pytest-asyncio==1.1.0`: Async test support
- `black==25.1.0`: Code formatting
- `ruff==0.12.3`: Fast Python linter (replaces flake8)
- `mypy==1.17.0`: Type checking
- `isort==6.0.1`: Import sorting

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