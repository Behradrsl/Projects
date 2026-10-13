"""A vertical point-mass plant and bounded PID controller, in SI units."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    kp: float = 3.0
    ki: float = 0.6
    kd: float = 3.5
    mass: float = 1.5
    target: float = 10.0
    max_thrust: float = 30.0
    disturbance: float = -3.0
    duration: float = 30.0
    dt: float = 0.02

    def validate(self):
        values = vars(self)
        if any(not math.isfinite(v) for v in values.values()):
            raise ValueError("All settings must be finite.")
        if min(self.kp, self.ki, self.kd, self.target, self.max_thrust) < 0:
            raise ValueError("Gains, target and thrust must be nonnegative.")
        if self.mass <= 0 or not 0.001 <= self.dt <= 0.05:
            raise ValueError("Mass must be positive; time step must be 0.001–0.05 s.")
        if not 20 <= self.duration <= 120:
            raise ValueError("Duration must be 20–120 s.")


def simulate(s: Settings):
    s.validate()
    z = velocity = integral = 0.0
    rows = []
    for step in range(round(s.duration / s.dt) + 1):
        t = step * s.dt
        error = s.target - z
        candidate = integral + error * s.dt
        raw = s.mass * 9.81 + s.kp * error + s.ki * candidate - s.kd * velocity
        # Conditional integration: allow integration back out of saturation.
        if (
            0 <= raw <= s.max_thrust
            or (raw > s.max_thrust and error < 0)
            or (raw < 0 and error > 0)
        ):
            integral = candidate
        demand = s.mass * 9.81 + s.kp * error + s.ki * integral - s.kd * velocity
        thrust = max(0.0, min(s.max_thrust, demand))
        wind = s.disturbance if 12 <= t < 16 else 0.0
        rows.append(
            {
                "Time (s)": t,
                "Altitude (m)": z,
                "Target (m)": s.target,
                "Thrust (N)": thrust,
                "Wind force (N)": wind,
                "Error (m)": error,
                "Saturated": demand < 0 or demand > s.max_thrust,
            }
        )
        acceleration = (thrust + wind - 0.25 * velocity) / s.mass - 9.81
        velocity += acceleration * s.dt
        z += velocity * s.dt
        if z < 0:
            z = velocity = 0.0
    return rows


def summarize(rows, target):
    tolerance = max(0.02 * target, 0.1)
    # Settling after the disturbance: every subsequent sample stays in band.
    last_out = max(
        (
            i
            for i, r in enumerate(rows)
            if r["Time (s)"] >= 16 and abs(r["Error (m)"]) > tolerance
        ),
        default=-1,
    )
    settling = None
    if last_out < len(rows) - 1:
        settling = max(16.0, rows[last_out + 1]["Time (s)"])
    return {
        "RMSE (m)": math.sqrt(sum(r["Error (m)"] ** 2 for r in rows) / len(rows)),
        "Overshoot (m)": max(0.0, max(r["Altitude (m)"] for r in rows) - target),
        "Final error (m)": rows[-1]["Error (m)"],
        "Recovery time after wind (s)": None if settling is None else settling - 16,
        "Saturation (%)": 100 * sum(r["Saturated"] for r in rows) / len(rows),
    }
