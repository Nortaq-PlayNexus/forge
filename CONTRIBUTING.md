# Contributing to Forge

Thank you for your interest in contributing! Forge is an open-source universal deploy engine.

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) — participation is governed by it.

## Ways to Contribute

- **Report bugs** — open an issue with a clear reproduction.
- **Suggest features** — open an issue using the feature request template.
- **Add cloud providers** — extend Forge with new provider support.
- **Add stack detectors** — improve tech stack detection.
- **Add tests** — improve coverage.

## Development Setup

```bash
git clone https://github.com/your-org/forge.git
cd forge
pip install -e .
forge detect
```

## Code Standards

- **Python 3.10+** — type hints required.
- Run tests before submitting PRs.

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org):

```
feat: add DigitalOcean provider
fix: handle missing Dockerfile gracefully
docs: update supported stacks list
```

## Opening a Pull Request

1. Create a branch from `main`.
2. Make focused, reviewable changes.
3. Open the PR with a clear description.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
