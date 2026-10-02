"""Scenario comparison and batch execution with bounded, isolated inputs."""

import copy
from . import analyze

MAX_CASES = 100


def apply_patch(document, path, value):
    """Set an existing value using RFC 6901 pointer escaping; never create fields."""
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("patch path must be a non-root JSON pointer")
    tokens = path[1:].split("/")
    decoded = []
    for token in tokens:
        index = 0
        while index < len(token):
            if token[index] == "~":
                if index + 1 >= len(token) or token[index + 1] not in "01":
                    raise ValueError("invalid JSON pointer escape")
                index += 2
            else:
                index += 1
        decoded.append(token.replace("~1", "/").replace("~0", "~"))
    current = document
    for index, token in enumerate(decoded):
        if isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise ValueError("invalid array index")
            key = int(token)
            if key >= len(current):
                raise ValueError("array index out of bounds")
        elif isinstance(current, dict):
            if token not in current:
                raise ValueError("patch field does not exist")
            key = token
        else:
            raise ValueError("patch traverses scalar value")
        if index == len(decoded) - 1:
            current[key] = copy.deepcopy(value)
        else:
            current = current[key]


def compare(left, right, path=""):
    """Return changed scalar paths, preserving exact values and their types."""
    rows = []
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            pointer = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key not in left or key not in right:
                rows.append(
                    {
                        "path": pointer,
                        "before": left.get(key),
                        "after": right.get(key),
                        "kind": "added" if key not in left else "removed",
                    }
                )
            else:
                rows.extend(compare(left[key], right[key], pointer))
    elif isinstance(left, list) and isinstance(right, list):
        for index in range(max(len(left), len(right))):
            pointer = path + "/" + str(index)
            if index >= len(left) or index >= len(right):
                rows.append(
                    {
                        "path": pointer,
                        "before": left[index] if index < len(left) else None,
                        "after": right[index] if index < len(right) else None,
                        "kind": "added" if index >= len(left) else "removed",
                    }
                )
            else:
                rows.extend(compare(left[index], right[index], pointer))
    elif type(left) is not type(right) or left != right:
        rows.append({"path": path, "before": left, "after": right, "kind": "changed"})
    return rows


def run_scenarios(base, cases):
    """Evaluate named independent scenarios and compare each against the base."""
    if (
        not isinstance(base, dict)
        or not isinstance(cases, list)
        or len(cases) > MAX_CASES
    ):
        raise ValueError("object input and at most 100 scenarios required")
    baseline = analyze(copy.deepcopy(base))
    results = []
    names = set()
    for case in cases:
        name = case["name"]
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("unique nonempty scenario names required")
        names.add(name)
        patches = case["patches"]
        if not isinstance(patches, list) or len(patches) > 100:
            raise ValueError("at most 100 patches per scenario")
        document = copy.deepcopy(base)
        try:
            for patch in patches:
                apply_patch(document, patch["path"], patch["value"])
            output = analyze(document)
            results.append(
                {
                    "name": name,
                    "status": "ok",
                    "input": document,
                    "result": output,
                    "changes": compare(baseline, output),
                }
            )
        except (ValueError, KeyError, TypeError, ArithmeticError) as error:
            results.append({"name": name, "status": "error", "error": str(error)})
    return {"baseline": baseline, "scenarios": results}


def run_batch(documents):
    if not isinstance(documents, list) or not 1 <= len(documents) <= MAX_CASES:
        raise ValueError("batch requires 1 to 100 documents")
    results = []
    for index, document in enumerate(documents):
        try:
            if not isinstance(document, dict):
                raise ValueError("document must be an object")
            results.append(
                {
                    "index": index,
                    "status": "ok",
                    "result": analyze(copy.deepcopy(document)),
                }
            )
        except (ValueError, KeyError, TypeError, ArithmeticError) as error:
            results.append({"index": index, "status": "error", "error": str(error)})
    return {
        "results": results,
        "successful": sum(r["status"] == "ok" for r in results),
        "failed": sum(r["status"] == "error" for r in results),
    }
