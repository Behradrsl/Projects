"""Human engineering judgments kept separate from automated language checks."""

from dataclasses import dataclass

STRUCTURAL_CRITERIA = (
    "Components are owned by a system assembly.",
    "Requested communication has connected, directed data flows.",
    "Requested behavior consumes the intended component inputs.",
)
REVIEW_STATES = ("Not reviewed", "Pass", "Partial", "Fail", "Not applicable")


@dataclass(frozen=True)
class ReviewEntry:
    loop: int
    category: str
    criterion: str
    assessment: str = "Not reviewed"
    evidence: str = ""


def criteria_rows(result):
    saved = {(r.loop, r.category, r.criterion): r for r in result.reviews}
    rows = []
    for record in result.iterations:
        for category, criteria in (
            ("Structure", STRUCTURAL_CRITERIA),
            ("Requirement", result.settings.requirements),
        ):
            for criterion in criteria:
                entry = saved.get(
                    (record.loop, category, criterion),
                    ReviewEntry(record.loop, category, criterion),
                )
                rows.append(
                    {
                        "Loop": entry.loop,
                        "Category": entry.category,
                        "Criterion": entry.criterion,
                        "Assessment": entry.assessment,
                        "Evidence": entry.evidence,
                    }
                )
    return rows


def save_reviews(result, rows, secrets=()):
    expected = {(r["Loop"], r["Category"], r["Criterion"]) for r in criteria_rows(result)}
    seen, entries = set(), []
    for row in rows:
        key = (row["Loop"], row["Category"], row["Criterion"])
        if key not in expected or key in seen:
            raise ValueError("Review rows must match this run's frozen criteria and versions.")
        seen.add(key)
        state, evidence = row["Assessment"], row["Evidence"]
        if state not in REVIEW_STATES or not isinstance(evidence, str) or len(evidence) > 2000:
            raise ValueError("Use a listed assessment and evidence of at most 2,000 characters.")
        if state != "Not reviewed" and not evidence.strip():
            raise ValueError("Add evidence or a reason for every assessment you make.")
        for secret in secrets:
            if secret:
                evidence = evidence.replace(secret, "[REDACTED]")
        entries.append(ReviewEntry(*key, state, evidence))
    if seen != expected:
        raise ValueError("Every version and configured criterion must remain in the review.")
    return tuple(entries)


def review_measurements(result, loop):
    entries = [r for r in result.reviews if r.loop == loop]
    values = {}
    for category, criteria, field in (
        ("Structure", STRUCTURAL_CRITERIA, "structural"),
        ("Requirement", result.settings.requirements, "requirement"),
    ):
        group = [r for r in entries if r.category == category]
        complete = (
            bool(criteria)
            and len(group) == len(criteria)
            and all(r.assessment != "Not reviewed" for r in group)
        )
        applicable = [r for r in group if r.assessment != "Not applicable"]
        values[f"manual_{field}_pass_percent"] = (
            100 * sum(r.assessment == "Pass" for r in applicable) / len(applicable)
            if complete and applicable
            else None
        )
        values[f"manual_{field}_reviewed"] = sum(r.assessment != "Not reviewed" for r in group)
    return values
