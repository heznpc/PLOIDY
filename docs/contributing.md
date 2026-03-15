# Contributing

Ploidy is in pre-alpha. Contributions are welcome -- especially from people interested in multi-agent debate, MCP tooling, or structured decision-making.

## Development Setup

### 1. Clone and install

```bash
git clone https://github.com/heznpc/ploidy.git
cd ploidy
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv venv
source .venv/bin/activate
```

### 3. Install in development mode

```bash
pip install -e ".[dev,docs]"
```

This installs:

- The `ploidy` package in editable mode
- **dev** dependencies: `pytest`, `pytest-asyncio`, `ruff`
- **docs** dependencies: `mkdocs-material`, `mkdocs-minify-plugin`

### 4. Verify the setup

```bash
# Run the server
ploidy

# Run tests
pytest

# Check code style
ruff check src/
ruff format --check src/
```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_protocol.py
```

Tests use `pytest-asyncio` for async test support. The `asyncio_mode = "auto"` setting in `pyproject.toml` means you don't need to decorate async tests with `@pytest.mark.asyncio`.

## Code Style

Ploidy uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
# Check for lint errors
ruff check src/

# Auto-fix lint errors
ruff check --fix src/

# Check formatting
ruff format --check src/

# Auto-format
ruff format src/
```

Configuration is in `pyproject.toml`:

- Target: Python 3.11+
- Line length: 100
- Rules: `E` (pycodestyle), `F` (pyflakes), `I` (isort), `N` (pep8-naming), `W` (warnings), `UP` (pyupgrade)

## Conventions

- All public functions must have docstrings
- Type hints on all function signatures
- Async-first -- use `async def` for any I/O-bound operations
- Domain exceptions inherit from `PloidyError` (see `src/ploidy/exceptions.py`)

## Docs Development

To preview the documentation site locally:

```bash
mkdocs serve
```

This starts a local server at `http://127.0.0.1:8000` with live reload.

## Pull Request Process

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Ensure tests pass: `pytest`
5. Ensure code style passes: `ruff check src/ && ruff format --check src/`
6. Submit a pull request with a clear description of the change

## Good First Issues

If you're looking for a place to start, these are concrete tasks that would be valuable:

- **Add parameterized queries to `store.py`** -- The current SQL queries use `?` placeholders but the pattern should be validated and made consistent across all methods. (Security, ~1 hour)

- **Add `asyncio.Lock` to phase transitions** -- The `DebateProtocol.advance_phase()` method needs concurrency protection. Two sessions calling it simultaneously could cause a race condition. (~1 hour)

- **Write protocol state machine tests** -- `protocol.py` defines a state machine with valid transitions. Write tests that verify: valid transitions succeed, invalid transitions raise `ProtocolError`, messages are rejected for wrong phases. (~2 hours)

- **Add structured logging** -- Replace `assert` statements with proper logging using Python's `logging` module. Add log points for debate lifecycle events (created, joined, position submitted, converged). (~2 hours)

- **Implement `debate/join` tool** -- The server currently has `debate_start` but no `debate_join` tool for Fresh sessions. Implement it: accept a `debate_id`, assign the Fresh role, return only the debate prompt. (~3 hours)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code. Please report unacceptable behavior by opening an issue.
