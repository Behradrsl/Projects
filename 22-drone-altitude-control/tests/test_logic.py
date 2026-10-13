import unittest
from dataclasses import replace

from control import Settings, simulate, summarize


class ControlTests(unittest.TestCase):
    def test_hover_and_limits(self):
        rows = simulate(Settings(target=0, disturbance=0))
        self.assertTrue(all(r["Altitude (m)"] == 0 for r in rows))
        self.assertAlmostEqual(rows[0]["Thrust (N)"], 14.715)
        rows = simulate(Settings(max_thrust=10))
        self.assertTrue(all(0 <= r["Thrust (N)"] <= 10 for r in rows))
        self.assertEqual(rows[-1]["Altitude (m)"], 0)
        self.assertIsNone(summarize(rows, 10)["Recovery time after wind (s)"])

    def test_convergence_and_step_consistency(self):
        s = Settings()
        a = simulate(s)
        b = simulate(replace(s, dt=0.01))
        self.assertLess(abs(a[-1]["Error (m)"]), 0.1)
        self.assertLess(abs(a[-1]["Altitude (m)"] - b[-1]["Altitude (m)"]), 0.03)
        self.assertTrue(any(r["Wind force (N)"] == -3 for r in a))

    def test_invalid_input(self):
        for s in [Settings(mass=0), Settings(kp=float("nan")), Settings(dt=1)]:
            with self.assertRaises(ValueError):
                simulate(s)
