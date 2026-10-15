"""Render the recorded sample without a provider request or a validator rerun.

Optional tooling: python -m pip install vl-convert-python
Run from the project folder: python scripts/render_sample.py
"""

from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import vl_convert as vlc

ROOT = Path(__file__).resolve().parents[1]
SCORES = {
    "syntax_score": "Syntax",
    "semantic_score": "Static semantics",
    "name_score": "Identifier presence",
}


def chart(rows, fields, colors, *, title, width, height, y_title, percentage=False):
    data = []
    for field, label in fields.items():
        segment = 0
        for row in rows:
            value = row[field]
            if value is None:
                segment += 1
            data.append(
                {
                    "Loop": row["loop"],
                    "Measure": label,
                    "Value": value,
                    "Segment": f"{field}:{segment}",
                }
            )
    return (
        alt.Chart(pd.DataFrame(data))
        .transform_filter("isValid(datum.Value)")
        .mark_line(point=alt.OverlayMarkDef(size=65), strokeWidth=2.5)
        .encode(
            x=alt.X(
                "Loop:Q",
                axis=alt.Axis(values=[r["loop"] for r in rows], format="d"),
                scale=alt.Scale(domain=[0.8, max(r["loop"] for r in rows) + 0.2]),
            ),
            y=alt.Y(
                "Value:Q",
                title=y_title,
                scale=alt.Scale(domain=[0, 100]) if percentage else alt.Scale(zero=True),
            ),
            color=alt.Color(
                "Measure:N",
                title=None,
                scale=alt.Scale(domain=list(fields.values()), range=colors),
                legend=alt.Legend(orient="bottom", columns=3),
            ),
            detail="Segment:N",
        )
        .properties(title=title, width=width, height=height)
    )


def main():
    record = json.loads((ROOT / "results.json").read_text())
    rows = record["measurements"]
    trajectory = chart(
        rows,
        SCORES,
        ["#6D7891", "#087F8C", "#A76516"],
        title="Validation trajectory",
        y_title="Automated check score",
        width=820,
        height=260,
        percentage=True,
    )
    passing = chart(
        rows,
        {"cumulative_pass_rate": "Passing versions"},
        ["#173A5E"],
        title="Cumulative check-pass",
        y_title="Versions passing (%)",
        width=385,
        height=160,
        percentage=True,
    )
    diagnostics = chart(
        rows,
        {"semantic_error_count": "Errors", "semantic_warning_count": "Warnings"},
        ["#087F8C", "#A76516"],
        title="Semantic diagnostics",
        y_title="Diagnostic count",
        width=385,
        height=160,
    )
    figure = (
        alt.vconcat(
            trajectory,
            alt.hconcat(passing, diagnostics, spacing=35).resolve_scale(color="independent"),
            spacing=35,
        )
        .resolve_scale(color="independent")
        .configure(background="#F7F9FC")
        .configure_view(stroke=None)
        .configure_axis(
            labelColor="#435970",
            titleColor="#435970",
            gridColor="#DCE4ED",
            labelFontSize=12,
            titleFontSize=12,
            titleFontWeight="normal",
        )
        .configure_title(color="#173A5E", fontSize=20, anchor="start", offset=15)
        .configure_legend(labelColor="#435970", labelFontSize=12)
    )
    (ROOT / "docs/sample-results.png").write_bytes(vlc.vegalite_to_png(figure.to_dict(), scale=2))
    print("Created docs/sample-results.png from results.json")


if __name__ == "__main__":
    main()
