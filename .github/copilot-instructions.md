# GitHub Copilot Instructions

This file provides repository-specific instructions for GitHub Copilot.

## Project Context

This is a Python project managed with pyproject.toml. Please refer to the project's CONVENTIONS.md file for detailed coding standards.

## Key Preferences

- **Python Version**: Use Python 3.x features as specified in pyproject.toml
- **Dependencies**: This project uses pyproject.toml for dependency management, not requirements.txt
- **Code Style**: Follow PEP 8 with 88-character line length (Black formatting)
- **Type Hints**: Always include type hints for function parameters and return values
- **String Formatting**: Prefer f-strings over .format() or % formatting
- **Imports**: Organize as: standard library, third-party, local imports

## Testing Approach

- Use pytest for testing (if applicable)
- Write tests for all new functionality
- Place tests in a `tests/` directory
- Use descriptive test names that explain the expected behavior

## Documentation Style

- Use Google-style docstrings for functions and classes
- Keep README.md updated with new features
- Include usage examples in docstrings when helpful

## Error Handling

- Use specific exception types, avoid bare `except:`
- Include meaningful error messages
- Log errors with appropriate context

## File Operations

- Use `pathlib.Path` instead of `os.path` for file operations
- Use context managers (`with` statements) for file handling
- Handle file encoding explicitly when needed

## Configuration Management

- Read configuration from pyproject.toml when appropriate
- Use environment variables for sensitive data
- Validate configuration early in the application lifecycle