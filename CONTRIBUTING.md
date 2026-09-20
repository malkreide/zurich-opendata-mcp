# Contributing to zurich-opendata-mcp

🌐 **English** | **[Deutsch](CONTRIBUTING.de.md)**

Thank you for your interest in contributing! This server is part of the
[Swiss Public Data MCP Portfolio](https://github.com/malkreide).

---

## Reporting Issues

Use [GitHub Issues](https://github.com/malkreide/zurich-opendata-mcp/issues) to
report bugs or request features.

Please include:
- Python version and OS
- Full error message or description of unexpected behaviour
- Steps to reproduce

---

## Setting Up the Development Environment

```bash
git clone https://github.com/malkreide/zurich-opendata-mcp.git
cd zurich-opendata-mcp

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install with dev dependencies
pip install -e ".[dev]"
```

---

## Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes and add tests
4. Ensure all tests pass: `pytest tests/ -m "not live"`
5. Ensure linting is clean: `ruff check src/ tests/`
6. Commit using [Conventional Commits](https://www.conventionalcommits.org/): `feat: add new tool`
7. Push and open a Pull Request against `main`

Keep one PR per feature/bugfix, and update documentation in **both** English
and German (`README.md` / `README.de.md`).

### The `Codex-Verdikt` check: why your PR may sit red for two minutes

Marking a draft ready triggers a Codex review, and that review takes **two to
three minutes**. Nothing about the merge button waits for it. Between the 18th
and 20th of September 2026 the "Codex review answered" checkbox in this
repository was ticked four times in a row on PRs where no review had happened;
on three of them the review only *started* after the merge, measured from the
timestamps Codex publishes in its summary table.

So the review is a check now, not a checkbox. `.github/workflows/codex-gate.yml`
reports a check run named `Codex-Verdikt`, and
`scripts/check_codex_verdict.py` decides what counts:

| Observed | Counts as a verdict? |
|---|---|
| A review object on the current head | yes — findings exist, answer them |
| "Didn't find any major issues" naming the current commit | yes |
| The summary table on `Completed`, nothing else | **no** |
| The summary table on `Running` | no, still working |
| Quota or missing-environment message | no, the review did not happen |

The third row is the one worth knowing. When a review finishes on a PR that is
already closed, the table says `Completed` and no verdict ever arrives —
"completed" tells you the run finished, not how it went.

The commit matters: a push does **not** re-trigger Codex. A verdict on an
earlier commit is not a verdict on yours; re-trigger by commenting
`@codex review`.

**If you genuinely need to merge without a review** — the quota is exhausted,
or the change cannot wait — add the label `codex-review-waived`. The check then
passes and records in its summary that it was waived. An escape hatch you can
see in the log beats one nobody notices.

---

## Adding a New Tool

1. **API client** (`src/zurich_opendata_mcp/clients/`): if connecting a new API,
   add the client module and any constants to `config.py`.
2. **Tool module** (`src/zurich_opendata_mcp/tools/`):
   - Define a Pydantic `BaseModel` for the inputs (`extra="forbid"`)
   - Implement an `@mcp.tool()` function with `readOnlyHint: True`
   - Return a Markdown-formatted response via the helpers in `formatters.py`
3. **Tests** (`tests/test_server.py`): add unit tests; use `respx` to mock the
   upstream API. Live integration tests are marked with `@pytest.mark.live`.
4. **README.md / README.de.md**: add the tool description and an example query
   in both languages.
5. **CHANGELOG.md**: add an entry under `[Unreleased]` (see `CLAUDE.md`).

---

## Code Style

- Python 3.11+
- [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Type hints required for all public functions
- Tests required for new tools (`tests/test_server.py`)
- Follow the existing FastMCP / Pydantic v2 patterns in `src/zurich_opendata_mcp/`

---

## Data Sources

All APIs used are publicly accessible and require no authentication. Data is
published under CC0 or comparable open licenses.

| Source | Documentation |
|--------|--------------|
| CKAN | [data.stadt-zuerich.ch/api/3/](https://data.stadt-zuerich.ch/api/3/) |
| Geoportal WFS | [www.ogd.stadt-zuerich.ch/wfs/geoportal](https://www.ogd.stadt-zuerich.ch/wfs/geoportal) |
| Paris (City Parliament) | [www.gemeinderat-zuerich.ch/api](https://www.gemeinderat-zuerich.ch/api) |
| Zürich Tourism | [www.zuerich.com/en/api/v2/data](https://www.zuerich.com/en/api/v2/data) |
| SPARQL | [ld.stadt-zuerich.ch/query](https://ld.stadt-zuerich.ch/query) |
| ParkenDD | [api.parkendd.de/Zuerich](https://api.parkendd.de/Zuerich) |

---

## The live suite: when it runs, and who sees a red result

**Cadence:** every Monday at 04:43 UTC, plus on demand via *Actions → Live-Tests → Run
workflow*. See [`.github/workflows/live-tests.yml`](.github/workflows/live-tests.yml).

**Who sees it:** A red run opens an issue labelled `upstream` and the stable title “Live-Tests gegen data.stadt-zuerich.ch rot (<Datum>)”. A second red run recognises the open issue by its title prefix and appends to that same thread rather than opening a second one. Once the suite is green again, the issue closes itself.

**Three answers, not two.** `scripts/classify_live_run.py` reads the JUnit XML rather than
the exit code and separates `clear` (ran, green), `finding` (ran, something
fell) and `unknown` (did not run — install failed, nothing collected,
everything skipped). An `unknown` never closes an issue: closing would claim a
comparison that never happened.

**A red live run does not necessarily mean *our* bug.** It means the contract
with the source has changed, or the source is down. Both belong seen; only the
first belongs fixed. Please read the run before disabling the job — that is how
this check dies, and it is the only one in the repository that can contradict a
wrong assumption about data.stadt-zuerich.ch. Every other test asserts against a fixture, and
the fixture was written from the same assumption as the code.

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).
