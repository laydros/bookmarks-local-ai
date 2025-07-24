# Bookmark Intelligence System

A local RAG-powered system for enriching and analyzing bookmark collections using Ollama and ChromaDB.

## Features

- **Bookmark Enrichment**: Automatically generate descriptions and tags for bookmarks using local LLM
- **RAG-Powered Context**: Uses your existing enriched bookmarks to maintain consistency
- **Smart Search**: Semantic search across your bookmark collection
- **Duplicate Detection**: Find potential duplicate bookmarks
- **Gap Analysis**: Identify missing topics in your collection
- **Auto-Categorization**: Suggest which file/category new bookmarks belong in
- **Category Suggestions**: AI-powered analysis to propose new organizational categories using HDBSCAN or k-means clustering
- **Bookmark Importer**: Load new bookmarks from JSON, HTML, Markdown, or plain URL lists with automatic duplicate detection and link verification

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
# Use a .csv extension to save results in Raindrop CSV format
python bookmark_enricher.py bookmarks.json --output enriched.csv
```

Enrich all JSON files in a directory:
```bash
python bookmark_enricher.py json/ --directory
```

Process a limited number of bookmarks:
```bash
python bookmark_enricher.py json/ --directory --limit 10
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

**Category suggestions** - Analyze your collection and propose new organizational categories:
```bash
python bookmark_intelligence.py json/ --suggest-categories

# Force k-means clustering with specific number of categories (2-10 recommended)
python bookmark_intelligence.py json/ --suggest-categories --use-kmeans 5

# Save suggestions to a markdown file for review
python bookmark_intelligence.py json/ --suggest-categories --output-md category_suggestions.md
```

**Create new category** - Create empty category files for organization:
```bash
python bookmark_intelligence.py json/ --create-category "3d-printing"
python bookmark_intelligence.py json/ --create-category "web-development"
```

**Populate categories intelligently** - Find and move bookmarks to specific categories:
```bash
# Find bookmarks that belong in the 3d-printing category
python bookmark_intelligence.py json/ --populate-category "3d-printing"

# Use filename format (both work identically)
python bookmark_intelligence.py json/ --populate-category "3d-printing.json"

# Customize suggestions (default: limit=5, threshold=0.85)
python bookmark_intelligence.py json/ --populate-category "web-development" --limit 10 --threshold 0.8
```

**Import new bookmarks** - Validate, categorize, and check for duplicates:
```bash
python bookmark_importer.py json/ new_bookmarks.json
# Or import from browser HTML/Markdown/plain text
python bookmark_importer.py json/ exported_bookmarks.html
# Or import from a Raindrop.io CSV export
python bookmark_importer.py json/ exported_bookmarks.csv

# Skip duplicate checking for faster import (not recommended)
python bookmark_importer.py json/ new_bookmarks.json --no-duplicate-check
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
- `create <category>` - Create new empty category file
- `help` - Show available commands
- `quit` - Exit interactive mode

**Note**: The `--populate-category` feature is only available via CLI, not in interactive mode.

## Project Structure

```
bookmarks-local-ai/
├── bookmark_enricher.py          # Main enrichment tool
├── bookmark_intelligence.py      # Smart search and analysis tool
├── bookmark_importer.py          # Import tool with duplicate detection
├── core/                         # Shared utilities
│   ├── models.py                 # Data models and validation
│   ├── bookmark_loader.py        # File I/O operations
│   ├── vector_store.py           # ChromaDB operations
│   ├── web_extractor.py          # Web content extraction
│   ├── backup_manager.py         # Backup utilities
│   ├── config_manager.py         # Configuration management
│   ├── category_manager.py       # Category creation and population
│   ├── category_suggester.py     # AI-powered category suggestions
│   └── progress_tracker.py       # Progress tracking
├── tests/                        # Test suite
│   ├── conftest.py               # Test configuration
│   ├── test_models.py            # Data model tests
│   ├── test_bookmark_loader.py   # File I/O tests
│   ├── test_vector_store.py      # Vector database tests
│   ├── test_web_extractor.py     # Web scraping tests
│   ├── test_enhanced_enricher.py # Enhanced enrichment tests
│   ├── test_category_manager.py  # Category management tests
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

CSV files exported from Raindrop.io are also supported. The columns should be
`link`, `title`, `excerpt`, `tags`, and `type`. Any CLI command will read or
write in this format automatically when the path ends with `.csv`.

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
- `test_bookmark_importer.py` - Import functionality tests
- `test_duplicate_detection.py` - Duplicate detection tests
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

### Category Management Workflow

The bookmark intelligence system provides a complete workflow for organizing your collection:

**1. Discover Categories**: Use `--suggest-categories` to analyze your collection and discover natural groupings
**2. Create Categories**: Use `--create-category` to create empty category files for organization
**3. Populate Categories**: Use `--populate-category` to intelligently find and move bookmarks to specific categories

**Category Population Process**:
- Uses semantic search to find bookmarks similar to the category name
- Shows high-confidence matches (default threshold: 0.85) with scores and source files
- Presents small batches (default: 5 suggestions) for user approval
- Allows selective approval: accept all, none, or choose specific bookmarks
- Safely moves bookmarks between files and updates all affected JSON files
- Can be run repeatedly to gradually populate categories over time

**Example Workflow**:
```bash
# 1. Discover what categories might be useful
python bookmark_intelligence.py bookmarks/ --suggest-categories

# 2. Create a specific category you want
python bookmark_intelligence.py bookmarks/ --create-category "3d-printing"

# 3. Populate it gradually (run multiple times)
python bookmark_intelligence.py bookmarks/ --populate-category "3d-printing"
# Review suggestions, select ones to move
# Re-run to find more candidates
```

### Category Suggestion Algorithms

The `--suggest-categories` feature uses clustering algorithms to group similar bookmarks and suggest new organizational categories.

**HDBSCAN (Default)**:
- **What it does**: Finds natural clusters of similar bookmarks by analyzing their semantic embeddings (vector representations of their content)
- **How it works**: Identifies "dense regions" where bookmarks have very similar content, leaving outliers ungrouped
- **Pros**: Discovers organic groupings, handles different cluster sizes well, doesn't force inappropriate groupings
- **Cons**: May find fewer clusters than expected if your bookmarks don't have strong natural groupings
- **Best for**: Collections with clear thematic groups (e.g., separate clusters for "Python tutorials", "Machine learning papers", "Cooking recipes")

**K-means (Fallback/Forced)**:
- **What it does**: Divides your bookmarks into exactly K groups by minimizing the "distance" between bookmarks in each group
- **How it works**: Like sorting items into K bins such that items in each bin are as similar as possible to each other
- **Pros**: Always produces exactly the number of categories you specify, more predictable results
- **Cons**: May create artificial groupings, struggles with clusters of very different sizes
- **Best for**: When you want a specific number of categories regardless of natural groupings

**Usage Recommendations**:
- Try default HDBSCAN first - it will find the most meaningful natural groupings
- Use `--use-kmeans 5` if HDBSCAN finds too few categories or you want exactly N categories
- Start with 3-8 categories - more becomes hard to manage, fewer may be too broad

**Example**: With 2000 bookmarks about programming, HDBSCAN might find 6 natural clusters (Python, JavaScript, DevOps, Databases, Frontend, Backend), while k-means with k=8 would force exactly 8 groups even if some are artificially split.

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
- [x] Import duplicate detection (URL, title, and content similarity)
- [x] Category suggestions with HDBSCAN and k-means clustering
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
