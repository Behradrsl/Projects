"""A small dashboard for observing automated SysML validation trajectories."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from config import load_connection
from engine import (
    DEFAULT_PROMPT,
    AttemptRecord,
    IterationRecord,
    OpenAIChatGenerator,
    RunResult,
    RunSettings,
    best_model,
    export_csv,
    export_json,
    rows_for_run,
    run_loop,
)
from review import REVIEW_STATES, ReviewEntry, criteria_rows, save_reviews
from validator import Diagnostic, ValidationResult

ROOT = Path(__file__).resolve().parent
SCORE_LABELS = {
    "syntax_score": "Syntax",
    "semantic_score": "Semantics",
    "name_score": "Identifier presence",
}
SCORE_COLORS = ["#6D7891", "#087F8C", "#A76516"]


def format_number(value: int | float | None, *, digits: int = 1) -> str:
    """Make unavailable values explicit without inventing a zero."""
    if value is None or pd.isna(value):
        return "N/A"
    if digits == 0:
        return f"{value:,.0f}"
    return f"{value:,.{digits}f}".rstrip("0").rstrip(".")


def expected_names_from_text(text: str) -> tuple[str, ...]:
    """One name per line, with duplicates rejected rather than silently removed."""
    names = tuple(line.strip() for line in text.splitlines() if line.strip())
    if len(names) > 30:
        raise ValueError("Use at most 30 expected names, one per line.")
    if any(len(name) > 80 for name in names):
        raise ValueError("Each expected name must contain at most 80 characters.")
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError("Expected names must be unique, ignoring letter case.")
    return names


def prompt_from_upload(upload: Any) -> str:
    if upload is None:
        return DEFAULT_PROMPT
    try:
        prompt = upload.getvalue().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Save the uploaded prompt as a UTF-8 .txt or .md file.") from exc
    if not prompt.strip():
        raise ValueError("The uploaded system prompt is empty.")
    if len(prompt) > 8_000:
        raise ValueError("The system prompt must contain at most 8,000 characters.")
    return prompt


def plot_records(rows: list[dict[str, Any]], metrics: dict[str, str]) -> list[dict[str, Any]]:
    """Keep raw measurements and separate line segments around missing checks."""
    data: list[dict[str, Any]] = []
    for field, label in metrics.items():
        segment = 0
        for row in rows:
            value = row.get(field)
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
    return data


def measurement_chart(
    rows: list[dict[str, Any]],
    metrics: dict[str, str],
    *,
    colors: list[str],
    height: int,
    y_title: str,
    percentage: bool = False,
) -> alt.Chart:
    data = pd.DataFrame(plot_records(rows, metrics))
    loops = [row["loop"] for row in rows]
    scale = alt.Scale(domain=[0, 100]) if percentage else alt.Scale(zero=True)
    return (
        alt.Chart(data)
        .transform_filter("isValid(datum.Value)")
        .mark_line(point=alt.OverlayMarkDef(size=65), strokeWidth=2.5)
        .encode(
            x=alt.X(
                "Loop:Q",
                scale=alt.Scale(domain=[0.75, max(loops) + 0.25]),
                axis=alt.Axis(values=loops, format="d", grid=False),
            ),
            y=alt.Y("Value:Q", title=y_title, scale=scale),
            color=alt.Color(
                "Measure:N",
                scale=alt.Scale(domain=list(metrics.values()), range=colors),
                legend=alt.Legend(
                    title=None,
                    orient="bottom",
                    columns=min(2, len(metrics)),
                    symbolStrokeWidth=3,
                ),
            ),
            detail="Segment:N",
            tooltip=[
                alt.Tooltip("Loop:Q", format="d"),
                alt.Tooltip("Measure:N"),
                alt.Tooltip("Value:Q", format=".2f"),
            ],
        )
        .properties(
            height=height,
            autosize=alt.AutoSizeParams(type="fit-x", contains="padding"),
        )
        .configure_view(stroke=None)
        .configure_axis(
            labelColor="#435970",
            titleColor="#435970",
            gridColor="#DCE4ED",
            domainColor="#DCE4ED",
            titleFontWeight="normal",
            labelFontSize=12,
            titleFontSize=12,
        )
        .configure_legend(labelColor="#435970", labelFontSize=12)
    )


def table_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Presentation only; exports and charts use the same unmodified rows."""
    return [
        {
            "Loop": row["loop"],
            "Generation": row.get("generation_state", "generated"),
            "Syntax": format_number(row.get("syntax_score")),
            "Semantics": format_number(row.get("semantic_score")),
            "Identifier presence": format_number(row.get("name_score")),
            "Pass": row["passed"],
            "Source changed": row.get("source_changed"),
            "Diagnostics resolved": row.get("resolved_diagnostics"),
            "New diagnostics": row.get("new_diagnostics"),
            "Errors": row["error_count"],
            "Warnings": row["warning_count"],
            "Input tokens": format_number(row["input_tokens"], digits=0),
            "Output tokens": format_number(row["output_tokens"], digits=0),
            "Total tokens": format_number(row["total_tokens"], digits=0),
            "Reasoning tokens": format_number(row.get("reasoning_tokens"), digits=0),
            "Cumulative tokens": format_number(row["cumulative_tokens"], digits=0),
            "Cumulative pass %": format_number(row["cumulative_pass_rate"]),
        }
        for row in rows
    ]


def show_validation_details(record: Any) -> None:
    st.caption(
        f"Parser: {record.validation.parse_state}. "
        f"Semantic analysis: {record.validation.semantic_state}."
    )
    if record.name_score is not None:
        st.caption(f"Identifier presence: {format_number(record.name_score)}%.")
    diagnostics = list(record.validation.diagnostics) + list(record.validation.warnings)
    if diagnostics:
        st.dataframe(
            [
                {
                    "Stage": item.stage,
                    "Severity": item.severity,
                    "Message": item.message,
                    "Line": item.line,
                    "Column": item.column,
                }
                for item in diagnostics
            ],
            hide_index=True,
            width="stretch",
            alt=f"Validation diagnostics for loop {record.loop}",
        )
    else:
        st.markdown("No diagnostics were reported.")
    if record.validation.missing_names:
        st.markdown("Missing expected names:")
        st.text("\n".join(record.validation.missing_names))


def version_label(record: Any) -> str:
    if record.passed:
        state = "passed"
    elif record.validation.parse_state == "unavailable" or (
        record.validation.parse_state == "valid"
        and record.validation.semantic_state == "unavailable"
    ):
        state = "validation unavailable"
    else:
        state = "did not pass"
    return (
        f"Loop {record.loop}: {state} — syntax {record.validation.parse_state}, "
        f"semantics {record.validation.semantic_state}"
    )


def show_versions(result: Any) -> None:
    st.subheader("Generated versions")
    if not result.iterations:
        st.info("No generated version was available for validation.")
    if result.failed_loops:
        st.warning(
            "No model was returned for loop(s) " + ", ".join(map(str, result.failed_loops)) + "."
        )
    best_loop = result.best.loop if result.best else None
    for record in result.iterations:
        with st.expander(
            version_label(record),
            expanded=record.loop == best_loop,
            key=f"version-{result.run_id}-{record.loop}",
        ):
            st.code(record.code, language=None, line_numbers=True, wrap_lines=True, height=300)
            st.download_button(
                f"Download loop {record.loop}",
                data=record.code,
                file_name=f"loop_{record.loop:02d}.sysml",
                mime="text/plain",
                key=f"download-version-{result.run_id}-{record.loop}",
                on_click="ignore",
            )
            show_validation_details(record)


def show_frozen_settings(result: Any) -> None:
    with st.expander("Settings used for this run"):
        st.write(f"Model: {result.settings.model}")
        st.write(f"Requested loops: {result.settings.iterations}")
        st.write(f"Maximum output tokens per request: {result.settings.max_output_tokens}")
        st.write(
            "Stop after first passing version: " + ("Yes" if result.settings.early_stop else "No")
        )
        st.write("CPS description:")
        st.text(result.settings.description)
        st.write("Expected names:")
        st.text("\n".join(result.settings.expected_names) or "None configured")
        st.write("Human review requirements:")
        st.text("\n".join(result.settings.requirements) or "None configured")
        st.write("Effective system prompt:")
        st.text(result.settings.system_prompt)
        st.caption(f"Run {result.run_id}. Started {result.started_at}.")


def show_engineering_review(result: Any, secrets=()) -> None:
    st.subheader("Engineering review")
    if not result.iterations:
        return
    review_rows = criteria_rows(result)
    selected_loop = st.selectbox(
        "Version to review",
        [record.loop for record in result.iterations],
        format_func=lambda loop: f"Loop {loop}",
        key=f"review-loop-{result.run_id}",
    )
    indices = [i for i, row in enumerate(review_rows) if row["Loop"] == selected_loop]
    selected_index = st.selectbox(
        "Criterion to review",
        indices,
        format_func=lambda i: f"{review_rows[i]['Category']}: {review_rows[i]['Criterion']}",
        key=f"review-criterion-{result.run_id}-{selected_loop}",
    )
    selected = review_rows[selected_index]
    editor_key = f"review-{result.run_id}-{selected_index}"
    with st.form(f"engineering-{editor_key}"):
        assessment = st.selectbox(
            "Assessment",
            REVIEW_STATES,
            index=REVIEW_STATES.index(selected["Assessment"]),
            key=f"assessment-{editor_key}",
        )
        evidence = st.text_area(
            "Model evidence or reason",
            value=selected["Evidence"],
            max_chars=2000,
            key=f"evidence-{editor_key}",
        )
        submitted = st.form_submit_button("Save engineering review")
    if submitted:
        review_rows[selected_index] = dict(selected, Assessment=assessment, Evidence=evidence)
        try:
            entries = save_reviews(result, review_rows, secrets)
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["completed_run"] = replace(
                result, reviews=entries, reviewed_at=datetime.now(timezone.utc).isoformat()
            )
            st.rerun()
    st.dataframe(
        criteria_rows(result),
        hide_index=True,
        width="stretch",
        alt="Saved human assessment and model evidence for each engineering criterion",
    )
    rows = rows_for_run(result)
    st.dataframe(
        [
            {
                "Loop": row["loop"],
                "Structure criteria met % (human)": format_number(
                    row["manual_structural_pass_percent"]
                ),
                "Requirements met % (human)": format_number(row["manual_requirement_pass_percent"]),
            }
            for row in rows
        ],
        hide_index=True,
        width="stretch",
        alt="Human structural and requirement assessments per loop; unreviewed values are N/A",
    )
    if any(
        row["manual_structural_pass_percent"] is not None
        or row["manual_requirement_pass_percent"] is not None
        for row in rows
    ):
        st.altair_chart(
            measurement_chart(
                rows,
                {
                    "manual_structural_pass_percent": "Structure (human)",
                    "manual_requirement_pass_percent": "Requirements (human)",
                },
                colors=["#087F8C", "#A76516"],
                height=230,
                y_title="Criteria fully met (%)",
                percentage=True,
            ),
            alt="Human structural and requirement criteria fully met across versions",
        )


def show_results(result: Any, secrets=()) -> None:
    if result.failed_loops:
        st.header(
            f"Processed {result.processed_loops} of {result.settings.iterations} loops · "
            f"{len(result.iterations)} generated versions"
        )
    else:
        st.header(f"Completed {len(result.iterations)} of {result.settings.iterations} loops")
    st.caption("Offline replay" if result.mode == "demo" else result.settings.model)
    accepted = sum(record.passed for record in result.iterations)
    if result.status == "validator_unavailable":
        st.error("Validator unavailable. The run stopped.")
    elif accepted:
        st.success(f"{accepted} of {len(result.iterations)} versions passed all configured checks.")
    else:
        st.warning("No version passed all configured automated checks.")
    if result.status == "generation_failed":
        st.error("Generation stopped. See Provider attempts for details.")
    elif result.status == "completed_with_failures":
        st.warning("All requested loops were attempted. Failed responses have no model or score.")
    if result.reason:
        st.caption(result.reason)
    if result.status == "early_stopped":
        st.caption("Stopped after the first passing version.")
    show_frozen_settings(result)

    best = result.best
    columns = st.columns(4)
    syntax_checked = [r for r in result.iterations if r.syntax_score is not None]
    semantic_checked = [r for r in result.iterations if r.semantic_score is not None]
    columns[0].metric(
        "Syntax passes",
        f"{sum(r.syntax_score == 100 for r in syntax_checked)}/{len(syntax_checked)}"
        if syntax_checked
        else "N/A",
    )
    columns[1].metric("Best loop", str(best.loop) if best else "N/A")
    columns[2].metric(
        "Semantic passes",
        f"{sum(r.semantic_score == 100 for r in semantic_checked)}/{len(semantic_checked)}"
        if semantic_checked
        else "N/A",
    )
    columns[3].metric("Reported tokens", format_number(result.cumulative_tokens, digits=0))

    score_tab, versions_tab, review_tab, attempts_tab = st.tabs(
        ["Validation dashboard", "Generated versions", "Engineering review", "Provider attempts"]
    )
    with score_tab:
        rows = rows_for_run(result)
        st.subheader("Validation trajectory")
        if rows:
            metrics = dict(SCORE_LABELS)
            colors = list(SCORE_COLORS)
            if not result.settings.expected_names:
                metrics.pop("name_score")
                colors.pop()
            st.altair_chart(
                measurement_chart(
                    rows,
                    metrics,
                    colors=colors,
                    height=320,
                    y_title="Automated check score",
                    percentage=True,
                ),
                width="stretch",
                alt="Automated, syntax, semantic and optional expected-name scores per loop",
            )
            left, right = st.columns(2)
            with left:
                st.subheader("Cumulative check-pass")
                st.altair_chart(
                    measurement_chart(
                        rows,
                        {"cumulative_pass_rate": "Passing versions"},
                        colors=["#173A5E"],
                        height=195,
                        y_title="Versions passing (%)",
                        percentage=True,
                    ),
                    width="stretch",
                    alt="Cumulative percentage of checked versions passing all configured checks",
                )
            with right:
                st.subheader("Semantic diagnostics")
                st.altair_chart(
                    measurement_chart(
                        rows,
                        {
                            "semantic_error_count": "Errors",
                            "semantic_warning_count": "Warnings",
                        },
                        colors=["#087F8C", "#A76516"],
                        height=195,
                        y_title="Diagnostic count",
                    ),
                    width="stretch",
                    alt="Semantic errors and warnings per loop; unavailable checks are omitted",
                )
            st.subheader("Cumulative provider tokens")
            if any(row["cumulative_tokens"] is not None for row in rows):
                st.altair_chart(
                    measurement_chart(
                        rows,
                        {"cumulative_tokens": "Reported input + output"},
                        colors=["#6D7891"],
                        height=160,
                        y_title="Reported tokens",
                    ),
                    width="stretch",
                    alt="Cumulative provider-reported input and output token counts per loop",
                )
            else:
                st.info("Token usage unavailable.")
            st.subheader("Per-loop measurements")
            st.dataframe(
                table_rows(rows),
                hide_index=True,
                width="stretch",
                column_config={"Pass": st.column_config.CheckboxColumn("Pass")},
                alt="Per-loop scores, changes, acceptance, diagnostics counts and reported tokens",
            )
        else:
            st.info("No completed loops.")
    with versions_tab:
        show_versions(result)
    with review_tab:
        show_engineering_review(result, secrets)
    with attempts_tab:
        st.subheader("Provider attempts")
        st.dataframe(
            [asdict(a) for a in result.attempts],
            hide_index=True,
            width="stretch",
            alt="Per-loop API attempts, safe failure reasons and reported token counts",
        )
    st.subheader("Export this run")
    best_text = best_model(result)
    model_column, csv_column, json_column = st.columns(3)
    model_column.download_button(
        "Download best SysML v2",
        data=best_text or "",
        file_name="best.sysml",
        mime="text/plain",
        disabled=best_text is None,
        width="stretch",
    )
    csv_column.download_button(
        "Download loop scores",
        data=export_csv(result),
        file_name="loop_scores.csv",
        mime="text/csv",
        width="stretch",
    )
    json_column.download_button(
        "Download full record",
        data=export_json(result),
        file_name="run_record.json",
        mime="application/json",
        width="stretch",
    )


def perform_run(settings: RunSettings, generator: Any) -> None:
    with st.status("Running validation loops…", expanded=True) as status:
        progress = st.progress(0, text=f"Preparing loop 1 of {settings.iterations}")
        version_slot = st.empty()
        live_versions = version_slot.container()

        def update(record: Any) -> None:
            progress.progress(
                record.loop / settings.iterations,
                text=(
                    f"Loop {record.loop} of {settings.iterations}: "
                    f"syntax {record.validation.parse_state}, "
                    f"semantics {record.validation.semantic_state}"
                ),
            )
            # Append checked candidates without rerunning the script or calling the model.
            with live_versions:
                st.markdown(f"**{version_label(record)}**")
                st.code(
                    record.code,
                    language=None,
                    line_numbers=True,
                    wrap_lines=True,
                    height=220,
                )

        def attempt_update(attempt):
            if attempt.state == "failed":
                st.warning(
                    f"Loop {attempt.loop}/{settings.iterations}, "
                    f"attempt {attempt.attempt}/2: {attempt.message}"
                )
                progress.progress(
                    (attempt.loop - 1) / settings.iterations,
                    text=f"Loop {attempt.loop} response failed; "
                    + (
                        "retrying"
                        if attempt.retryable and attempt.attempt == 1
                        else "see provider status"
                    ),
                )

        try:
            result = run_loop(settings, generator, on_iteration=update, on_attempt=attempt_update)
        finally:
            # Completed results below contain one persistent viewer per version.
            version_slot.empty()
        st.session_state["completed_run"] = result
        progress.progress(
            result.processed_loops / settings.iterations,
            text=f"Processed {result.processed_loops} of {settings.iterations} loops",
        )
        status.update(
            label=(
                f"Processed {result.processed_loops} of {settings.iterations} loops; "
                f"{len(result.iterations)} generated versions"
            ),
            state=(
                "error"
                if result.status
                in {"generation_failed", "validator_unavailable", "completed_with_failures"}
                else "complete"
            ),
            expanded=False,
        )


def upgrade_session_result(result):
    """Preserve a previous run when Streamlit reloads the revised data classes."""
    if isinstance(result, RunResult) and hasattr(result.settings, "max_output_tokens"):
        return result
    payload = asdict(result)
    settings = RunSettings(**payload.pop("settings"))
    records = []
    for candidate in payload.pop("iterations"):
        validation = candidate.pop("validation")
        for field in ("diagnostics", "warnings"):
            validation[field] = tuple(Diagnostic(**item) for item in validation[field])
        records.append(IterationRecord(**candidate, validation=ValidationResult(**validation)))
    payload["attempts"] = tuple(AttemptRecord(**item) for item in payload.get("attempts", ()))
    payload["reviews"] = tuple(ReviewEntry(**item) for item in payload.get("reviews", ()))
    # This path upgrades the original record schema, without rerunning or rescoring it.
    return RunResult(settings=settings, iterations=tuple(records), **payload)


def main() -> None:
    connection = load_connection(ROOT)
    st.set_page_config(page_title="Agentic MBSE Loop", layout="wide")
    st.title("Agentic MBSE Loop")
    st.write("Generate, validate and refine SysML v2 models through iterative feedback.")

    with st.sidebar:
        st.header("Model connection")
        model = st.text_input("Model ID", value=connection.model, key="model_id")
        base_url = st.text_input(
            "API base URL", value=connection.base_url or "", key="api_base_url"
        )
        entered_key = st.text_input("API key", type="password")

    with st.form("run_configuration"):
        st.subheader("Run settings")
        loop_column, stop_column = st.columns([1, 2], vertical_alignment="bottom")
        with loop_column:
            iterations = st.number_input(
                "Number of loops",
                min_value=1,
                max_value=8,
                value=4,
                step=1,
                key="number_of_loops",
            )
        with stop_column:
            stop_after_pass = st.checkbox(
                "Stop after first passing version",
                value=False,
                key="stop_after_pass",
                wrap=True,
            )
        description = st.text_area(
            "CPS description",
            height=170,
            max_chars=20_000,
            key="cps_description",
        )
        with st.expander("Advanced settings"):
            expected = st.text_area(
                "Expected names (one per line)",
                height=100,
                key="expected_names",
            )
            upload = st.file_uploader("System prompt", type=["txt", "md"], max_upload_size=1)
            requirements_text = st.text_area(
                "Human review requirements (one per line)",
                key="review_requirements",
            )
            max_output_tokens = st.number_input(
                "Maximum output tokens per request",
                min_value=1024,
                max_value=32768,
                value=8192,
                step=1024,
                key="max_output_tokens",
            )
        submitted = st.form_submit_button("Run validation", type="primary", width="stretch")

    if submitted:
        try:
            settings = RunSettings(
                description=description,
                system_prompt=prompt_from_upload(upload),
                expected_names=expected_names_from_text(expected),
                iterations=int(iterations),
                early_stop=stop_after_pass,
                model=model.strip(),
                base_url=base_url.strip() or None,
                max_output_tokens=int(max_output_tokens),
                requirements=tuple(
                    line.strip() for line in requirements_text.splitlines() if line.strip()
                ),
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            key = entered_key.strip() or connection.api_key
            if not key:
                st.error("Add an API key under Model connection.")
            else:
                try:
                    with OpenAIChatGenerator(
                        model=settings.model,
                        api_key=key,
                        base_url=settings.base_url,
                        max_output_tokens=settings.max_output_tokens,
                    ) as generator:
                        perform_run(settings, generator)
                except Exception:
                    st.error("The run could not finish. Check the connection and validator.")

    result = st.session_state.get("completed_run")
    if result is not None:
        result = upgrade_session_result(result)
        st.session_state["completed_run"] = result
        show_results(result, secrets=(connection.api_key, entered_key.strip()))


if __name__ == "__main__":
    main()
