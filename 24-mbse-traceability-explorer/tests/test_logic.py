import copy
import json
import unittest
from pathlib import Path

from model import impact, traceability, validate


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.model = json.loads(
            (
                Path(__file__).resolve().parents[1] / "examples/inspection_drone.json"
            ).read_text()
        )

    def test_coverage_and_outcomes(self):
        rows = traceability(self.model)
        self.assertEqual(sum(r["Link coverage"] for r in rows), 3)
        self.assertEqual(
            [r["Recorded test outcome"] for r in rows],
            ["pass", "not_run", "fail", "unlinked"],
        )

    def test_impact_and_cycles(self):
        result = impact(self.model, "C-NAV")
        self.assertEqual(result["Components"], ["C-CAM", "C-FC", "C-NAV"])
        self.assertEqual(result["Requirements"], ["REQ-01", "REQ-03"])
        self.model["links"].append(
            {"source": "C-NAV", "target": "C-CAM", "kind": "depends_on"}
        )
        self.assertEqual(impact(self.model, "C-NAV"), result)

    def test_integrity(self):
        for update in [{"target": "missing"}, {"kind": "verifies"}]:
            broken = copy.deepcopy(self.model)
            broken["links"][0].update(update)
            with self.assertRaises(ValueError):
                validate(broken)
