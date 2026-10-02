"""Search bounded token graphs, simulate reserve-mutating multihop routes and greedily allocate split trades."""

import json
from .engine import analyze
import argparse
import csv
import io
import sys
from pathlib import Path


def load_input(path):
    raw = Path(path).read_text(encoding="utf-8")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("invalid JSON constant: " + value)

    data = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    return data


def flatten(value, prefix=""):
    rows = []
    if isinstance(value, dict):
        for key, item in value.items():
            rows.extend(flatten(item, f"{prefix}.{key}" if prefix else key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            rows.extend(flatten(item, f"{prefix}[{index}]"))
    else:
        rows.append((prefix, json.dumps(value, ensure_ascii=False)))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON input file")
    parser.add_argument("--output", help="write result atomically to a file")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    args = parser.parse_args(argv)
    try:
        result = analyze(load_input(args.input))
        if args.format == "json":
            content = (
                json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
            )
        else:
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["path", "value"])
            writer.writerows(flatten(result))
            content = buffer.getvalue()
        if args.output:
            import os, tempfile

            target = Path(args.output)
            fd, temporary = tempfile.mkstemp(
                prefix="." + target.name + ".", dir=target.parent
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    stream.write(content)
                os.replace(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        else:
            sys.stdout.write(content)
    except (ValueError, KeyError, TypeError, OSError, ArithmeticError) as error:
        parser.exit(2, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
