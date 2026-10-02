# Dashboard and workflow API

## Start

Run `python3 -m cryptolab.server --port 8787 --db runs.sqlite3`. The server prints its loopback URL. Use Ctrl-C to close it. The default fixture path is relative to the working directory; pass `--example` for a different JSON file.

## Workflow

1. Load the example or import your JSON file.
2. Choose a single analysis, independent scenario comparison, or batch run. Changing mode reloads the fixture, so export or copy edits first.
3. Add an optional label and run.
4. Inspect structured output and scenario scalar differences.
5. Export the result or load an earlier run from the database.

All user data is inserted into the DOM as text. No CDN, telemetry, remote fonts or wallet libraries are used. The UI uses a responsive layout, visible focus states, labels and an accessible status region.

## Routes

| Route | Method | Payload / behavior |
|---|---|---|
| `/api/bootstrap` | GET | Session token, title and fixture; same-origin access |
| `/api/analyze` | POST | `{ "input": {}, "label": "" }` |
| `/api/scenarios` | POST | `{ "input": {}, "scenarios": [], "label": "" }` |
| `/api/batch` | POST | `{ "documents": [{}], "label": "" }` |
| `/api/runs` | GET | Latest 50 runs; optional `before` id cursor |
| `/api/runs/{id}` | GET | Full saved snapshot |

POST requests require `Content-Type: application/json`. All API requests except bootstrap require the bootstrap token in `X-Session-Token`. The Host must be `127.0.0.1:{port}`. There are no permissive CORS headers.

## Scenarios

Each scenario has a unique `name` and a `patches` array. Each patch contains `path` and `value`. Paths use JSON Pointer (`~1` for slash, `~0` for tilde), cannot address the root, and must refer to existing fields or array elements. At most 100 scenarios and 100 patches per scenario. Input documents are deep-copied for isolation. Output differences preserve strings, booleans and integers rather than coercing monetary values.

## Limits and retention

POST bodies and imported files are limited to 1 MiB. Batches have 1–100 documents. Labels have at most 200 characters. History is append-only and paginated; no retention pruning is implemented. Stop the server and archive or remove the SQLite file to reset history. Snapshots include supplied account identifiers and financial data.

SQLite commits each completed run atomically. SHA-256 identifies canonical input payloads; it is an integrity identifier rather than authentication. The HTTP server is single-threaded, intended for one local analyst; long analyses block later requests. Domain errors return 400; unknown runs return 404.
