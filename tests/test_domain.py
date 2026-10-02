import unittest, copy, json
from decimal import Decimal
from pathlib import Path
from cryptolab import analyze
from cryptolab.engine import *

EXAMPLE = json.loads(Path("examples/input.json").read_text())


class DomainTests(unittest.TestCase):
    def test_routes(self):
        self.assertEqual(analyze(EXAMPLE)["route_count"], 2)

    def test_split_input_conserved(self):
        self.assertEqual(
            sum(r["input"] for r in analyze(EXAMPLE)["split_allocations"]), 10000
        )

    def test_reserve_product(self):
        r = analyze(EXAMPLE)
        for p in EXAMPLE["pools"]:
            self.assertGreaterEqual(
                r["final_pools"][p["id"]]["reserve_a"]
                * r["final_pools"][p["id"]]["reserve_b"],
                p["reserve_a"] * p["reserve_b"],
            )

    def test_no_route(self):
        d = copy.deepcopy(EXAMPLE)
        d["target"] = "Z"
        with self.assertRaises(ValueError):
            analyze(d)

    def test_route_isolation(self):
        pools = {p["id"]: copy.deepcopy(p) for p in EXAMPLE["pools"]}
        before = copy.deepcopy(pools)
        execute_route(pools, ["ab", "bc"], "A", 100)
        self.assertEqual(pools, before)
