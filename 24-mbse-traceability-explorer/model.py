"""Validate a small JSON engineering model and derive traceability views."""

import json

KINDS = {"requirement", "component", "test", "interface"}
RULES = {
    "satisfies": ("component", "requirement"),
    "verifies": ("test", "requirement"),
    "connects": ("interface", "component"),
    "depends_on": ("component", "component"),
}


def validate(model):
    if not isinstance(model, dict) or set(model) != {"elements", "links"}:
        raise ValueError("Model needs exactly elements and links arrays.")
    if not isinstance(model["elements"], list) or not isinstance(model["links"], list):
        raise ValueError("Elements and links must be arrays.")
    if not 1 <= len(model["elements"]) <= 200 or len(model["links"]) > 1000:
        raise ValueError("Use 1–200 elements and at most 1000 links.")
    elements = {}
    for e in model["elements"]:
        if not isinstance(e, dict) or not {"id", "kind", "name"} <= e.keys():
            raise ValueError("Every element needs id, kind and name.")
        if any(
            not isinstance(e[k], str) or not e[k].strip() or len(e[k]) > 300
            for k in ("id", "kind", "name")
        ):
            raise ValueError(
                "Element fields must be nonempty strings up to 300 characters."
            )
        if e["kind"] not in KINDS or e["id"] in elements:
            raise ValueError("Unknown element kind or duplicate identifier.")
        if e["kind"] == "test" and e.get("status", "not_run") not in {
            "pass",
            "fail",
            "not_run",
        }:
            raise ValueError("Test status must be pass, fail or not_run.")
        elements[e["id"]] = e
    seen = set()
    for link in model["links"]:
        if not isinstance(link, dict) or set(link) != {"source", "target", "kind"}:
            raise ValueError("Each link needs source, target and kind.")
        if any(not isinstance(v, str) for v in link.values()):
            raise ValueError("Link fields must be strings.")
        a, b, kind = link["source"], link["target"], link["kind"]
        if a not in elements or b not in elements or kind not in RULES:
            raise ValueError("Dangling link or unknown relationship.")
        if (elements[a]["kind"], elements[b]["kind"]) != RULES[kind] or a == b:
            raise ValueError("Relationship has invalid endpoint types.")
        key = (a, b, kind)
        if key in seen:
            raise ValueError("Duplicate relationship.")
        seen.add(key)
    return elements


def traceability(model):
    elements = validate(model)
    rows = []
    for e in elements.values():
        if e["kind"] != "requirement":
            continue
        components = [
            link["source"]
            for link in model["links"]
            if link["kind"] == "satisfies" and link["target"] == e["id"]
        ]
        tests = [
            link["source"]
            for link in model["links"]
            if link["kind"] == "verifies" and link["target"] == e["id"]
        ]
        statuses = [elements[t].get("status", "not_run") for t in tests]
        outcome = (
            "unlinked"
            if not tests
            else "fail"
            if "fail" in statuses
            else "not_run"
            if "not_run" in statuses
            else "pass"
        )
        rows.append(
            {
                "Requirement": e["id"],
                "Description": e["name"],
                "Allocated components": ", ".join(components),
                "Verification cases": ", ".join(tests),
                "Link coverage": bool(components and tests),
                "Recorded test outcome": outcome,
            }
        )
    return rows


def impact(model, component):
    elements = validate(model)
    if component not in elements or elements[component]["kind"] != "component":
        raise ValueError("Select a component.")
    affected = {component}
    # A depends_on B: a change to B propagates to A, including cycles.
    while True:
        more = {
            link["source"]
            for link in model["links"]
            if link["kind"] == "depends_on" and link["target"] in affected
        }
        if more <= affected:
            break
        affected |= more
    requirements = {
        link["target"]
        for link in model["links"]
        if link["kind"] == "satisfies" and link["source"] in affected
    }
    tests = {
        link["source"]
        for link in model["links"]
        if link["kind"] == "verifies" and link["target"] in requirements
    }
    interfaces = {
        link["source"]
        for link in model["links"]
        if link["kind"] == "connects" and link["target"] in affected
    }
    return {
        "Components": sorted(affected),
        "Requirements": sorted(requirements),
        "Verification cases": sorted(tests),
        "Interfaces": sorted(interfaces),
    }


def diagram(model):
    elements = validate(model)
    lines = [
        "digraph model {",
        "rankdir=LR;",
        'node [fontname="Helvetica", style=filled];',
    ]
    colors = {
        "requirement": "#DBEAFE",
        "component": "#CCFBF1",
        "test": "#FEF3C7",
        "interface": "#EDE9FE",
    }
    for e in elements.values():
        label = json.dumps(e["id"] + chr(10) + e["name"])
        color = colors[e["kind"]]
        lines.append(f'{json.dumps(e["id"])} [label={label}, fillcolor="{color}"];')
    for link in model["links"]:
        source = json.dumps(link["source"])
        target = json.dumps(link["target"])
        kind = json.dumps(link["kind"])
        lines.append(f"{source} -> {target} [label={kind}];")
    return "\n".join(lines + ["}"])
