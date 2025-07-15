# CONTRIBUTING

> note: this codebase is currently (and historically) rather entangled with [osf.io](https://osf.io), which has its shtrove at https://share.osf.io/trove -- stay tuned for more-reusable open-source libraries and tools that should be more accessible to community contribution

For now, if you're interested in contributing to SHARE/trove, feel free to
[open an issue on github](https://github.com/CenterForOpenScience/SHARE/issues)
and start a conversation.

## Requirements

All new changes must pass the following checks with no errors:
- unit tests: `python -m pytest -x tests/`
- linting: `python -m flake8`
- static type-checking (on `trove/` code only, for now): `python -m mypy trove`

All new changes should also avoid decreasing test coverage, when reasonably possible.
