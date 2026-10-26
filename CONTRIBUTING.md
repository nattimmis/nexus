# Contributing to Nexus

Thank you for considering contributing to Nexus! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions. We're building a collaborative community.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a virtual environment: `python -m venv venv`
4. Activate it: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
5. Install for development: `pip install -e ".[dev]"`
6. Create a feature branch: `git checkout -b feature/your-feature`

## Development Workflow

### Code Style

We enforce consistent code style using:

- **Black** for formatting (100 char line length)
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Before committing, run:

```bash
black nexus tests examples
isort nexus tests examples
flake8 nexus tests examples --max-line-length=100 --extend-ignore=E203
mypy nexus --ignore-missing-imports
```

Or use the pre-commit hook (optional):

```bash
pip install pre-commit
pre-commit install
```

### Type Hints

All functions must have type hints. We aim for full mypy compliance.

```python
def process_waypoint(waypoint: Waypoint, timeout: float = 10.0) -> bool:
    """Process a waypoint with the given timeout."""
    ...
```

### Docstrings

Every function, class, and module must have a docstring following Google style:

```python
def record_action(
    action_type: ActionType,
    selector: Optional[str] = None,
    value: Optional[str] = None,
) -> None:
    """
    Record a navigation action.

    Args:
        action_type: Type of action to record.
        selector: CSS selector for the target element (optional).
        value: Value for type/fill actions (optional).

    Raises:
        ValueError: If required parameters are missing.
    """
    ...
```

### Testing

Write tests for all new functionality:

```python
def test_waypoint_hash_computation():
    """Test waypoint hash computation."""
    waypoint = Waypoint(url='https://example.com')
    waypoint.add_action(ActionType.CLICK, selector='#button')

    hash1 = waypoint.compute_hash()
    hash2 = waypoint.compute_hash()

    assert hash1 == hash2
```

Run tests before submitting:

```bash
pytest                      # Run all tests
pytest -v                   # Verbose
pytest --cov               # With coverage
pytest tests/test_waypoint.py  # Specific file
```

We aim for 90%+ test coverage.

## Submitting Changes

1. Commit with clear, descriptive messages:

```bash
git commit -m "Add support for XPath selectors in recorder"
```

2. Push to your fork:

```bash
git push origin feature/your-feature
```

3. Open a pull request on GitHub with:
   - Clear title and description
   - Reference to any related issues
   - Summary of changes
   - Test coverage information

4. Ensure all CI/CD checks pass (linting, tests, build)

## Pull Request Guidelines

- Keep PRs focused and reasonably sized
- Add tests for new functionality
- Update documentation as needed
- Ensure commit history is clean and logical
- Be responsive to review feedback

## Reporting Issues

Found a bug? Please open a GitHub issue with:

- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS
- Relevant error messages or logs

## Suggesting Features

Have an idea? Open a GitHub discussion or issue with:

- Clear use case and motivation
- Proposed solution (if applicable)
- Alternative approaches considered
- Potential impact on existing functionality

## Commit Message Format

Use clear, descriptive commit messages:

```
[type] Brief description under 50 chars

Optional longer explanation explaining why
this change is necessary. Wrap at 72 chars.

- List specific changes
- Use bullet points for clarity

Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `perf`, `ci`

## Documentation

- Update README.md for user-facing changes
- Add docstrings to all new functions
- Update examples if behavior changes
- Keep CHANGELOG.md current

## Release Process

Maintainers only:

1. Update version in `nexus/__init__.py`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v0.2.0`
4. Push: `git push origin main --tags`
5. GitHub Actions publishes to PyPI automatically

## Questions?

- Open a discussion on GitHub
- Check existing issues first
- Email: nattimmis@gmail.com

Thank you for contributing!
