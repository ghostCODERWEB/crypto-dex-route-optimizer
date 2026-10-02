import copy
import json
import tempfile
import unittest
from pathlib import Path
from cryptolab import analyze
from cryptolab.scenarios import apply_patch, compare, run_batch, run_scenarios
from cryptolab.store import RunStore
from cryptolab.server import parse_payload

EXAMPLE = json.loads(Path("examples/input.json").read_text())


class WorkflowTests(unittest.TestCase):
    def test_batch_partial_failure(self):
        result = run_batch([EXAMPLE, {}])
        self.assertEqual(result["successful"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["results"][0]["result"], analyze(EXAMPLE))

    def test_batch_limits(self):
        for documents in ([], [{}] * 101):
            with self.assertRaises(ValueError):
                run_batch(documents)

    def test_scenario_isolation(self):
        document = {"a": [{"b": 1}]}
        before = copy.deepcopy(document)
        modified = copy.deepcopy(document)
        apply_patch(modified, "/a/0/b", 2)
        self.assertEqual(document, before)
        self.assertEqual(modified["a"][0]["b"], 2)

    def test_pointer_escapes(self):
        doc = {"a/b": {"~x": 1}}
        apply_patch(doc, "/a~1b/~0x", 2)
        self.assertEqual(doc["a/b"]["~x"], 2)
        for pointer in ("", "/missing", "/a~2b", "/a~1b/~0x/0"):
            with self.assertRaises(ValueError):
                apply_patch(doc, pointer, 2)

    def test_noop_scenario(self):
        output = run_scenarios(EXAMPLE, [{"name": "same", "patches": []}])
        self.assertEqual(output["scenarios"][0]["changes"], [])
        self.assertEqual(output["baseline"], analyze(EXAMPLE))

    def test_bad_scenario_does_not_abort_others(self):
        output = run_scenarios(
            EXAMPLE,
            [
                {"name": "bad", "patches": [{"path": "/missing", "value": 1}]},
                {"name": "ok", "patches": []},
            ],
        )
        self.assertEqual([r["status"] for r in output["scenarios"]], ["error", "ok"])

    def test_compare_presence_and_types(self):
        rows = compare({"a": 1, "b": None}, {"a": True, "c": None})
        self.assertEqual([r["kind"] for r in rows], ["changed", "removed", "added"])

    def test_store_persistence_and_pagination(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "runs.db")
            store = RunStore(path)
            one = store.save("single", "first", EXAMPLE, analyze(EXAMPLE))
            two = store.save("single", "second", EXAMPLE, analyze(EXAMPLE))
            self.assertEqual(store.list(limit=1)["runs"][0]["id"], two)
            self.assertEqual(store.list(limit=1, before=two)["runs"][0]["id"], one)
            self.assertEqual(store.get(one)["checksum"], store.get(two)["checksum"])
            store.close()
            store = RunStore(path)
            self.assertEqual(store.get(one)["input"], EXAMPLE)
            with self.assertRaises(KeyError):
                store.get(999)
            store.close()

    def test_parse_payload(self):
        for raw in ("[]", '{"a":NaN}', '{"a":1,"a":2}'):
            with self.assertRaises(ValueError):
                parse_payload(raw)
