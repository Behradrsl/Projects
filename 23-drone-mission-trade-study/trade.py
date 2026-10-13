"""Screen mission alternatives before applying a transparent preference score."""

import math

CANDIDATES = [
    {
        "Name": "Scout",
        "Battery (Wh)": 120,
        "Power (W)": 260,
        "Payload limit (kg)": 0.4,
        "Cost (EUR)": 1200,
    },
    {
        "Name": "Surveyor",
        "Battery (Wh)": 220,
        "Power (W)": 390,
        "Payload limit (kg)": 0.9,
        "Cost (EUR)": 2200,
    },
    {
        "Name": "Carrier",
        "Battery (Wh)": 350,
        "Power (W)": 600,
        "Payload limit (kg)": 1.8,
        "Cost (EUR)": 3400,
    },
]


def evaluate(
    candidates,
    minutes=20.0,
    payload=0.6,
    budget=3000.0,
    reserve=0.2,
    endurance_weight=0.5,
):
    settings = (minutes, payload, budget, reserve, endurance_weight)
    if (
        any(not math.isfinite(v) for v in settings)
        or minutes <= 0
        or payload < 0
        or budget <= 0
        or not 0 <= reserve < 1
        or not 0 <= endurance_weight <= 1
    ):
        raise ValueError("Invalid mission settings.")
    if not candidates:
        raise ValueError("Supply at least one configuration.")
    results = []
    names = set()
    for c in candidates:
        if (
            not isinstance(c["Name"], str)
            or not c["Name"].strip()
            or c["Name"] in names
        ):
            raise ValueError("Configuration names must be nonempty and unique.")
        names.add(c["Name"])
        for key in ("Battery (Wh)", "Power (W)", "Payload limit (kg)", "Cost (EUR)"):
            if not math.isfinite(c[key]) or c[key] <= 0:
                raise ValueError(f"{key} must be positive and finite.")
        endurance = 60 * c["Battery (Wh)"] * (1 - reserve) / c["Power (W)"]
        margins = {
            "Endurance margin (min)": endurance - minutes,
            "Payload margin (kg)": c["Payload limit (kg)"] - payload,
            "Budget margin (EUR)": budget - c["Cost (EUR)"],
        }
        results.append(
            {
                **c,
                "Endurance (min)": endurance,
                **margins,
                "Feasible": all(v >= 0 for v in margins.values()),
                "Score": None,
            }
        )
    feasible = [r for r in results if r["Feasible"]]
    for r in feasible:
        # Fixed mission-relative scales avoid changing scores when alternatives change.
        benefit = min(r["Endurance (min)"] / (2 * minutes), 1.0)
        affordability = max(0.0, 1 - r["Cost (EUR)"] / budget)
        r["Score"] = 100 * (
            endurance_weight * benefit + (1 - endurance_weight) * affordability
        )
    return sorted(results, key=lambda r: (r["Feasible"], r["Score"] or 0), reverse=True)
