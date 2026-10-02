# DEX route and split optimizer

Search bounded token graphs, simulate reserve-mutating multihop routes and greedily allocate split trades.

An original AI-assisted research application with a domain state machine or analytical engine, local browser dashboard, batch/scenario workflows and SQLite history. Shared infrastructure is reused across the portfolio; domain logic and regression cases are specific to this project.

## Quick start

Python 3.11+ with no runtime dependencies.

```sh
python3 -m cryptolab examples/input.json
python3 -m unittest discover -s tests -v
python3 -m cryptolab.server --port 8787 --db runs.sqlite3
```

Open http://127.0.0.1:8787. Edit inputs, replay events, compare independent patched scenarios, process batches and inspect saved snapshots. Use different ports for parallel apps.

## Domain behavior

Constant-product integer pools only. Routes cannot revisit tokens. Greedy split allocation is a heuristic, not a global optimality guarantee; gas costs, MEV, stale reserves and transfer-tax tokens are excluded.

The engine is in [cryptolab/engine.py](cryptolab/engine.py); [tests](tests/test_domain.py) cover normal operation, boundary cases and rejected transitions. Inputs use integers or decimal strings for economics; statistical outputs deliberately use floating point. Read [model documentation](docs/model.md) before interpreting results.

## Features

- Domain-specific state and transition validation.
- Replay traces or detailed analytical output.
- Batch execution with per-document error isolation.
- JSON Pointer scenario patches with baseline comparison.
- Responsive local dashboard and saved run history.
- SQLite snapshots, canonical input checksums and pagination.
- JSON/CSV CLI and atomic output replacement.
- HTTP integration, domain and workflow regression tests.
- CI across Python 3.11–3.14.

## API

`from cryptolab import analyze` accepts the input object and returns JSON-compatible output. The full sample is [examples/input.json](examples/input.json). Dashboard routes and bounds are in [docs/dashboard.md](docs/dashboard.md).

Optional install: `python3 -m pip install -e .`. Each repository uses the `cryptolab` package name; use separate virtual environments.

## Status

Version 0.1.0, reference implementation. No independent audit, production deployment, live data integration or cryptographic identity verification is claimed. No wallets, funds or outside services are accessed. MIT licensed.
