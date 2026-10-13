import unittest

from trade import CANDIDATES, evaluate


class TradeTests(unittest.TestCase):
    def test_default_mission(self):
        rows = evaluate(CANDIDATES)
        feasible = [r for r in rows if r["Feasible"]]
        self.assertEqual([r["Name"] for r in feasible], ["Surveyor"])
        self.assertAlmostEqual(feasible[0]["Endurance (min)"], 60 * 220 * 0.8 / 390)
        self.assertTrue(all(r["Score"] is None for r in rows if not r["Feasible"]))
        self.assertFalse(any(r["Feasible"] for r in evaluate(CANDIDATES, minutes=45)))

    def test_boundary_and_preference(self):
        c = [
            {
                "Name": "A",
                "Battery (Wh)": 100,
                "Power (W)": 240,
                "Payload limit (kg)": 1,
                "Cost (EUR)": 1000,
            }
        ]
        self.assertTrue(evaluate(c, minutes=20, payload=1, budget=1000)[0]["Feasible"])
        a = evaluate(CANDIDATES, budget=4000, endurance_weight=0)[0]
        b = evaluate(CANDIDATES, budget=4000, endurance_weight=1)[0]
        self.assertNotEqual(a["Score"], b["Score"])
        self.assertEqual(a["Name"], "Surveyor")
        self.assertEqual(b["Name"], "Carrier")

    def test_reject_invalid(self):
        with self.assertRaises(ValueError):
            evaluate(CANDIDATES, reserve=1)
        with self.assertRaises(ValueError):
            evaluate([{**CANDIDATES[0], "Power (W)": 0}])
