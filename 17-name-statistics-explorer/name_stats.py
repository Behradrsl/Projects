"""Summarize supplied aggregate name counts without inferring personal traits."""

import csv
import io
import unicodedata
from collections import Counter


def load_records(data: bytes) -> list[dict]:
    if len(data) > 2_000_000:
        raise ValueError("Use a CSV smaller than 2 MB.")
    try:
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
        if not {"name", "region", "count"}.issubset(reader.fieldnames or []):
            raise ValueError("The CSV needs name, region, and count columns.")
        records = []
        for row in reader:
            name = unicodedata.normalize("NFC", (row.get("name") or "").strip())
            region = (row.get("region") or "").strip()
            count = int(row.get("count") or "")
            if not name or not region or not 0 <= count <= 1_000_000_000:
                raise ValueError(
                    "Each row needs a name, a region, and a nonnegative whole count."
                )
            records.append({"name": name, "region": region, "count": count})
            if len(records) > 20000:
                raise ValueError("Use at most 20,000 rows.")
    except UnicodeDecodeError as error:
        raise ValueError("Save the CSV using UTF-8 encoding.") from error
    except (TypeError, OverflowError) as error:
        raise ValueError("Counts must be nonnegative whole numbers.") from error
    if not records or sum(row["count"] for row in records) == 0:
        raise ValueError("Add at least one positive count.")
    return records


def summarize_name(records: list[dict], name: str) -> list[dict]:
    query = unicodedata.normalize("NFC", name.strip()).casefold()
    counts = Counter()
    for row in records:
        if row["name"].casefold() == query:
            counts[row["region"]] += row["count"]
    total = sum(counts.values())
    return (
        [
            {
                "region": region,
                "count": count,
                "share_percent": round(100 * count / total, 2),
            }
            for region, count in sorted(
                counts.items(), key=lambda pair: (-pair[1], pair[0])
            )
        ]
        if total
        else []
    )
