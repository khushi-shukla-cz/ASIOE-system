# Contributing

Small guide for contributors: run tests, format code, and open PRs.

Run tests locally:

```
backend\.venv\Scripts\activate.bat  # Windows
source backend/.venv/bin/activate     # Unix
python -m pytest backend -q
```

Run formatter:

```
black .
```

Please follow the project's coding standards and add tests for new features.
# Contributing to ASIOE

Thanks for wanting to contribute! Please follow these guidelines to make your PRs easier to review.

1. Fork the repository and create a branch per feature or fix: `git checkout -b feat/short-desc`.
2. Run linters and tests locally before opening a PR.
3. Write clear commit messages and reference related issues.
4. Add tests for new behavior when possible.
5. Update `README.md` for any user-facing changes or new environment variables.

Code style: follow existing project conventions. Keep changes small and focused.

If you're unsure where to start, open an issue and tag maintainers.
