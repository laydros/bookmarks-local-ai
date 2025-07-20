# Bookmark Intelligence System

A local RAG-powered system for enriching and analyzing bookmark collections using Ollama and ChromaDB.

## Features

- **Bookmark Enrichment**: Automatically generate descriptions and tags for bookmarks using local LLM
- **RAG-Powered Context**: Uses your existing enriched bookmarks to maintain consistency
- **Smart Search**: Semantic search across your bookmark collection
- **Duplicate Detection**: Find potential duplicate bookmarks
- **Gap Analysis**: Identify missing topics in your collection
- **Auto-Categorization**: Suggest which file/category new bookmarks belong in
- **Bookmark Importer**: Load new bookmarks from JSON, HTML, Markdown, or plain URL lists and verify links

## Requirements

- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running
- 8GB+ RAM recommended (for running local models)

## Installation

1. **Clone or set up the project**:
   ```bash
   git clone <your-repo> bookmarks
   cd bookmarks
   ```

2. **Set up Python environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the project**:
   ```bash
   # For development (recommended)
   pip install -e .[dev]
   
   # For production only
   pip install .
   ```

4. **Install and configure Ollama**:
   ```bash
   # Install Ollama (if not already installed)
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull required models
   ollama pull nomic-embed-text
   ollama pull llama3.1:8b
   
   # Start Ollama service
   ollama serve
   ```

## Usage

### Bookmark Enrichment

Enrich bookmarks in a single file:
```bash
python bookmark_enricher.py bookmarks.json
```

Enrich all JSON files in a directory:
```bash
python bookmark_enricher.py json/ --directory
```

Custom models:
```bash
python bookmark_enricher.py json/ --embedding-model mxbai-embed-large --llm-model mistral:7b
```

### Bookmark Intelligence

**Smart search** - Semantic search across your collection:
```bash
python bookmark_intelligence.py json/ --search "Python debugging tools"
python bookmark_intelligence.py json/ --search "machine learning" --results 5
```

**Find duplicates** - Detect duplicate bookmarks:
```bash
python bookmark_intelligence.py json/ --duplicates
```

**Analyze collection** - Get insights about your bookmarks:
```bash
python bookmark_intelligence.py json/ --analyze
```

**Auto-categorization** - Suggest which file a bookmark belongs to:
```bash
python bookmark_intelligence.py json/ --categorize "https://example.com"
```

**Import new bookmarks** - Validate and categorize new entries:
```bash
python bookmark_importer.py json/ new_bookmarks.json
# Or import from browser HTML/Markdown/plain text
python bookmark_importer.py json/ exported_bookmarks.html
```

**Interactive mode** - Explore your bookmarks interactively:
```bash
python bookmark_intelligence.py json/ --interactive
```

In interactive mode, available commands:
- `search <query>` - Search bookmarks
- `duplicates` - Find and optionally remove duplicate bookmarks
- `analyze` - Analyze collection statistics
- `categorize <url>` - Suggest category for URL
- `help` - Show available commands
- `quit` - Exit interactive mode

## Project Structure

```
bookmarks-local-ai/
├── bookmark_enricher.py          # Main enrichment tool
├── bookmark_intelligence.py      # Smart search and analysis tool
├── core/                         # Shared utilities
│   ├── models.py                 # Data models and validation
│   ├── bookmark_loader.py        # File I/O operations
│   ├── vector_store.py           # ChromaDB operations
│   ├── web_extractor.py          # Web content extraction
│   ├── backup_manager.py         # Backup utilities
│   ├── config_manager.py         # Configuration management
│   └── progress_tracker.py       # Progress tracking
├── tests/                        # Test suite
│   ├── conftest.py               # Test configuration
│   ├── test_models.py            # Data model tests
│   ├── test_bookmark_loader.py   # File I/O tests
│   ├── test_vector_store.py      # Vector database tests
│   ├── test_web_extractor.py     # Web scraping tests
│   ├── test_enhanced_enricher.py # Enhanced enrichment tests
│   └── fixtures/                 # Test data
├── pyproject.toml                # Project configuration and dependencies
└── CLAUDE.md                     # Claude Code instructions
```

## Bookmark Format

The system supports flexible bookmark formats:

```json
[
  {
    "url": "https://example.com",           // or "link"
    "title": "Example Site",
    "description": "Site description",     // or "excerpt" 
    "tags": ["tag1", "tag2"],
    "type": "link"
  }
]
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
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

# Check style (using ruff instead of flake8)
ruff check .

# Auto-fix issues
ruff check --fix .

# Type checking
mypy core/
```

### Test Structure

- `test_models.py` - Data model and validation tests
- `test_bookmark_loader.py` - File I/O and JSON processing tests  
- `test_web_extractor.py` - Web scraping and content extraction tests
- `test_vector_store.py` - ChromaDB and vector operations tests
- `test_config.py` - Configuration management tests
- `test_enhanced_enricher.py` - Enhanced enrichment functionality tests
- `conftest.py` - Shared test fixtures and configuration
- `fixtures/` - Sample test data and bookmark files

## Configuration

### Models

**Embedding Models** (choose one):
- `nomic-embed-text` (recommended, fast)
- `mxbai-embed-large` (higher quality, slower)

**LLM Models** (choose one):
- `llama3.1:8b` (recommended, good balance)
- `mistral:7b` (faster, slightly lower quality)
- `codellama:7b` (good for technical bookmarks)

### Performance Tuning

**Memory Usage** (approximate):
- `nomic-embed-text`: ~2GB
- `llama3.1:8b`: ~5-8GB  
- ChromaDB + Python: ~1-2GB
- **Total**: ~8-11GB

**Processing Speed**:
- ~2-5 bookmarks per minute (includes web scraping delays)
- Use `--no-delay` flag to process faster (be respectful to websites)

## Privacy & Security

- **100% Local**: All AI processing happens on your machine
- **No External APIs**: No data sent to OpenAI, Google, etc.
- **Private**: Your bookmarks never leave your computer
- **Offline Capable**: Works without internet (except for web scraping)

## Troubleshooting

### Common Issues

**lxml installation fails**:
```bash
# Try these in order:
pip install --upgrade pip
arch -arm64 pip install lxml --no-cache-dir  # M1/M2/M3 Macs
STATIC_DEPS=true pip install lxml             # Last resort
```

**Ollama connection refused**:
```bash
# Make sure Ollama is running
ollama serve

# Check if models are installed
ollama list
```

**Out of memory**:
- Use smaller models (`mistral:7b` instead of `llama3.1:8b`)
- Process bookmarks in smaller batches
- Close other applications

### Getting Help

1. Check the logs for specific error messages
2. Verify Ollama is running: `curl http://localhost:11434/api/tags`
3. Test with a small sample file first
4. Run tests to verify installation: `pytest tests/`

## Dependencies

This project uses `pyproject.toml` for dependency management. Key dependencies include:

**Core Dependencies:**
- `requests` - HTTP requests for web scraping
- `beautifulsoup4` - HTML parsing
- `chromadb` - Vector database for embeddings
- `ollama` - Local LLM integration
- `lxml` - Fast XML/HTML parsing

**Development Dependencies:**
- `pytest` - Testing framework
- `black` - Code formatting
- `ruff` - Fast linting (replaces flake8)
- `mypy` - Type checking
- `isort` - Import sorting

## Roadmap

- [x] Bookmark enrichment with RAG
- [x] Flexible JSON format support  
- [x] Comprehensive test suite
- [x] Configuration management
- [x] Backup and recovery utilities
- [x] Progress tracking and error reporting
- [x] Smart search functionality (`bookmark_intelligence.py`)
- [x] Duplicate detection
- [x] Auto-categorization
- [x] Interactive query interface
- [x] Collection analysis and insights
- [ ] Gap analysis (identify missing topics)
- [ ] Web UI (possible future enhancement)
- [ ] Bookmark recommendation engine
- [ ] Export/import to other bookmark managers

## Contributing

1. Set up development environment: `pip install -e .[dev]`
2. Run tests: `pytest`
3. Check code style: `black . && ruff check .`
4. Add tests for new features
5. Update documentation

## License

BSD-3-Clause License - see LICENSE file for details.

## Developer & Agent Docs

- [AGENTS.md](AGENTS.md)
- [CONVENTIONS.md](CONVENTIONS.md)
