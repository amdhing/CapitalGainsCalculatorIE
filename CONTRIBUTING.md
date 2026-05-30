# Contributing to Irish Capital Gains Calculator

First off, thanks for taking the time to contribute! 🎉

This project is a community-driven tool for Irish tax compliance, and every contribution — whether it's a bug report, feature request, documentation improvement, or code change — is valued.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

1. **Check existing issues** — Search the issue tracker to see if the bug has already been reported.
2. **Use the bug report template** — Provide a clear description, steps to reproduce, expected vs actual behavior, and your environment (OS, Python version, etc.).
3. **Include sample data** — If possible, attach anonymized transaction data that triggers the bug.

### Suggesting Features

1. **Describe the problem** — What are you trying to achieve? Why is the current implementation insufficient?
2. **Propose a solution** — How would you like the feature to work? Be specific enough to discuss.
3. **Check the project spec** — Review `docs/project_spec.md` and `docs/design/future_direction.md` to ensure the feature aligns with the project's direction.

### Pull Requests

1. **Fork the repository** and create your branch from `main` (or the appropriate feature branch).
2. **Run the tests** — Ensure all existing tests pass before making changes:
   ```bash
   cd tests && python -m pytest -v
   ```
3. **Add tests** — If you're adding a feature or fixing a bug, include test coverage.
4. **Update documentation** — If your change affects user-facing behavior, update `docs/` and `README.md` accordingly.
5. **Follow the style** — Python code should follow PEP 8. Frontend code should follow the existing React/Mantine patterns.
6. **Write clear commit messages** — Use conventional commits (e.g., `feat:`, `fix:`, `docs:`, `test:`).
7. **Open a PR** against `main` with a clear title and description linking to any related issues.

## Development Setup

```bash
# Clone and set up
git clone https://github.com/amdhing/CapitalGainsCalculatorIE.git
cd CapitalGainsCalculatorIE
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Run the CLI on sample data
python improved_calculator.py samples/sample_revolut_transactions.csv

# Web app (optional)
cd src/api && uvicorn main:app --reload --port 8000 &
cd frontend && npm install && npm run dev
```

## Project Structure

See the [Project Specification](docs/project_spec.md) for a full breakdown of the repository structure.

## Code Review Process

- All PRs require at least one review from a maintainer.
- Automated tests must pass before merging.
- Maintainers may request changes or ask for clarification.
- Once approved, a maintainer will merge your PR.

## License

By contributing, you agree that your contributions will be licensed under the project's [CC BY-NC-SA 4.0 License](LICENSE).
