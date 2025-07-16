# Project Conventions

This file provides coding conventions and project context for AI coding assistants like Aider.

## Project Overview

<!-- Brief description of your project -->
This is a Python project that [describe your project purpose].

## Development Environment

- **Python Version**: 3.x (check pyproject.toml for exact version)
- **Dependency Management**: Uses pyproject.toml with [pip/poetry/uv/etc]
- **Virtual Environment**: Use `python -m venv venv` or your preferred tool
- **Testing Framework**: [pytest/unittest/etc]
- **Linting**: [ruff/flake8/black/etc]

## Coding Standards

### Python Style
- Follow PEP 8 for code style
- Use type hints for all function parameters and return values
- Prefer f-strings for string formatting
- Use meaningful variable and function names
- Maximum line length: 88 characters (Black default)

### Code Organization
- Keep functions focused and small (< 50 lines typically)
- Use dataclasses or Pydantic models for structured data
- Organize imports: standard library, third-party, local imports
- Use absolute imports when possible

### Error Handling
- Use specific exception types, not bare `except:`
- Log errors with appropriate context
- Validate inputs early in functions
- Use context managers for resource management

### Documentation
- Write docstrings for all public functions and classes
- Use Google-style docstrings
- Include type information in docstrings when helpful
- Update README.md when adding new features

### Testing
- Write tests for all new functionality
- Use descriptive test names that explain what is being tested
- Follow Arrange-Act-Assert pattern
- Mock external dependencies in unit tests

## Project-Specific Guidelines

### Dependencies
- Only add dependencies that are truly necessary
- Pin version ranges in pyproject.toml
- Keep development dependencies separate from runtime dependencies
- Document why each major dependency was chosen

### Git Workflow
- Write clear, descriptive commit messages
- Use conventional commits format: `type(scope): description`
- Keep commits atomic (one logical change per commit)
- Include tests in the same commit as the feature they test

### Performance Considerations
- Profile before optimizing
- Use appropriate data structures (dict vs list vs set)
- Consider memory usage for large datasets
- Cache expensive computations when appropriate

## File Structure Preferences

- Configuration files in project root
- Source code in `src/` or package directory
- Tests in `tests/` directory mirroring source structure
- Documentation in `docs/` directory
- Scripts and utilities in `scripts/` or `bin/`

## When Making Changes

1. **Before coding**: Understand the existing patterns in the codebase
2. **During coding**: Follow the established conventions above
3. **After coding**: Run tests, linting, and formatting tools
4. **Before committing**: Review changes and update documentation if needed

## Common Patterns to Follow

- Use `pathlib.Path` instead of `os.path` for file operations
- Prefer `json.loads()` over `eval()` for data parsing
- Use context managers (`with` statements) for file operations
- Validate configuration and inputs early
- Use logging instead of print statements for debugging

## Common Anti-Patterns to Avoid

- Don't use global variables
- Don't ignore error cases
- Don't write overly complex one-liners
- Don't commit commented-out code
- Don't hardcode values that should be configurable
- Don't mix business logic with presentation logic