# CONTRIBUTING

> note: this codebase is currently (and historically) rather entangled with [osf.io](https://osf.io), which has its shtrove at https://share.osf.io -- stay tuned for more-reusable open-source libraries and tools that should be more accessible to community contribution

For now, if you're interested in contributing to SHARE/trove, feel free to
[open an issue on github](https://github.com/CenterForOpenScience/SHARE/issues)
and start a conversation.

## Required checks

All changes must pass the following checks with no errors:
- linting: `python -m flake8`
- static type-checking (on `trove/` code only, for now): `python -m mypy trove`
- tests: `python -m pytest -x tests/`
    - note: some tests require other services running -- if [using the provided docker-compose.yml](./how-to/run-locally.md), recommend running in the background (upping worker ups all: `docker compose up -d worker`) and executing tests from within one of the python containers (`indexer`, `worker`, or `web`):
        `docker compose exec indexer python -m pytest -x tests/`

All new changes should also avoid decreasing test coverage, when reasonably possible (currently checked on github pull requests).
