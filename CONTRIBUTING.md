# Contributing to aiphoria

Thank you for your interest in aiphoria! Contributions of all kinds are
welcome: bug reports, questions, documentation improvements, example
scenarios, tests, and code.

## Reporting bugs and asking for help

Please use the [GitHub issue tracker](https://github.com/EuropeanForestInstitute/aiphoria/issues)
for bug reports, questions, and feature suggestions. Check first whether a
similar issue already exists.

A good bug report includes:

- what you expected to happen and what happened instead
- the aiphoria version (`pip show aiphoria`), Python version, and operating system
- the full error message or log output
- if possible, a small Excel scenario file that reproduces the problem (remove
  any data you cannot share), and the settings you changed, for example
  `scenario_type`

For feature suggestions, describe the problem the feature would solve and how
you would use it. For larger changes, please open an issue to discuss the idea
before you start coding.

You can also contact the maintainers directly; see the contacts in the
[README](README.md).

## Setting up a development environment

You need Python 3.10 or newer and Git.

1. Fork the repository on GitHub and clone your fork:

   ```
   git clone https://github.com/YOUR-USERNAME/aiphoria.git
   cd aiphoria
   git remote add upstream https://github.com/EuropeanForestInstitute/aiphoria.git
   ```

2. Create and activate a virtual environment:

   ```
   python -m venv .venv
   source .venv/bin/activate        # macOS/Linux
   .venv\Scripts\activate           # Windows
   ```

3. Install aiphoria in editable mode, together with the development tools
   (pytest and pytest-cov):

   ```
   pip install -e .
   pip install --group dev          # needs pip 25.1 or newer
   ```

   With an older pip, install the tools directly: `pip install pytest pytest-cov`.

## Making changes

1. Create a branch from an up-to-date `main`:

   ```
   git checkout main
   git pull upstream main
   git checkout -b fix/short-description
   ```

2. Keep each pull request focused on one fix or feature.
3. Follow the existing code style (PEP 8, clear names, type hints and
   docstrings where useful).
4. Add or update tests for your change. When fixing a bug, add a test that
   would have caught it.
5. Run the test suite and make sure it passes:

   ```
   pytest
   ```

6. Update the [wiki](https://github.com/EuropeanForestInstitute/aiphoria/wiki)
   or the example scenario if your change affects how users set up or run a
   model (for example new settings, sheets, or columns in the Excel file).

## Opening a pull request

Push your branch to your fork and open a pull request against `main`. In the
description, explain what you changed, why, and how you tested it. Tests run
automatically on every pull request through GitHub Actions.

A maintainer will review your pull request and may ask for changes. If you
disagree with a suggestion, please explain why; review is a discussion.

## Code of conduct

Please be respectful and constructive in all project discussions.

## License

By contributing, you agree that your contributions will be licensed under the
project's [MIT License](LICENSE).
