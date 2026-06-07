import csv
import logging
import os
import shutil
from pathlib import Path
from collections import defaultdict

from utils.path_validation import validate_domain_id

logger = logging.getLogger(__name__)


def _publish_latest_file(source_file: Path, latest_file: Path):
    temp_path = latest_file.with_suffix(".tmp")
    try:
        shutil.copyfile(source_file, temp_path)
        # On Windows, os.replace is atomic and sufficient; fsync is not needed for most workflows.
        os.replace(temp_path, latest_file)
        return latest_file, None
    except Exception as e:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        return None, e

def export_entities_csv(
    entities,
    entity_events,
    entity_scores,
    overlay_ids,
    domain_id,
    output_path,
    should_suppress_entity_for_csv,
):
    entities_file = output_path / f"entities_dual_lens_{domain_id}.csv"

    filtered_entities = [
        entity
        for entity in entities
        if not should_suppress_entity_for_csv(entity, entity_events)
    ]

    with open(entities_file, "w", newline="", encoding="utf-8") as f:
        base_cols = ["entity_name", "entity_type", "entity_variant", "event_count"]
        overlay_cols = []

        for overlay_id in overlay_ids:
            overlay_cols.extend([
                f"{overlay_id}_score",
                f"{overlay_id}_bucket",
            ])

        writer = csv.DictWriter(f, fieldnames=base_cols + overlay_cols)
        writer.writeheader()

        for entity in filtered_entities:
            if not isinstance(entity, dict):
                continue

            entity_id = entity.get("entity_id")
            event_count = len(entity_events.get(entity_id, [])) if entity_id else 0

            row = {
                "entity_name": entity.get("entity_name", ""),
                "entity_type": entity.get("entity_type", ""),
                "entity_variant": entity.get("entity_variant") or "",
                "event_count": event_count,
            }

            for overlay_id in overlay_ids:
                overlay_scores = entity_scores.get(entity_id, {}).get(overlay_id)
                if overlay_scores:
                    row[f"{overlay_id}_score"] = f"{overlay_scores.get('score', 0):.2f}"
                    row[f"{overlay_id}_bucket"] = overlay_scores.get("bucket", "N/A")
                else:
                    row[f"{overlay_id}_score"] = ""
                    row[f"{overlay_id}_bucket"] = "N/A"

            writer.writerow(row)

    return entities_file, filtered_entities

def publish_latest_entities(entities_file: Path, domain_id: str):
    domain_id = validate_domain_id(domain_id)
    latest_dir = Path("exports") / "latest" / domain_id
    latest_dir.mkdir(parents=True, exist_ok=True)

    latest_entities_file = latest_dir / "entities_dual_lens.csv"
    return _publish_latest_file(entities_file, latest_entities_file)

def export_events_csv(
    events,
    event_overlay_scores,
    overlay_ids,
    domain_id,
    output_path,
):
    events_file = output_path / f"events_dual_lens_{domain_id}.csv"

    with open(events_file, "w", newline="", encoding="utf-8") as f:
        base_cols = [
            "event_id",
            "event_type",
            "stage",
            "confidence_original",
            "evidence_snippet",
        ]
        overlay_cols = [f"{overlay_id}_score" for overlay_id in overlay_ids]

        writer = csv.DictWriter(f, fieldnames=base_cols + overlay_cols)
        writer.writeheader()

        for event in events:
            if isinstance(event, dict):
                event_dict = event
            elif hasattr(event, "as_dict"):
                event_dict = event.as_dict()
            else:
                event_dict = dict(event)
            event_id = event_dict.get("event_id") or ""
            snippet = event_dict.get("evidence_snippet") or ""

            row = {
                "event_id": event_id,
                "event_type": event_dict.get("event_type", ""),
                "stage": event_dict["stage"],
                "confidence_original": event_dict.get("confidence", "unknown"),
                "evidence_snippet": snippet[:200] + ("..." if len(snippet) > 200 else ""),
            }

            for overlay_id in overlay_ids:
                score = event_overlay_scores.get(event_id, {}).get(overlay_id, 0)
                row[f"{overlay_id}_score"] = f"{score:+.1f}"

            writer.writerow(row)

    return events_file

def publish_latest_events(events_file: Path, domain_id: str):
    domain_id = validate_domain_id(domain_id)
    latest_dir = Path("exports") / "latest" / domain_id
    latest_dir.mkdir(parents=True, exist_ok=True)

    latest_events_file = latest_dir / "events_dual_lens.csv"
    return _publish_latest_file(events_file, latest_events_file)

def write_dual_lens_report(
    report_file: Path,
    domain_config: dict,
    overlay_ids: list[str],
    events,
    entities,
    filtered_entities,
    entity_scores,
    entity_events,
):
    domain_name = "<unknown domain>"
    if isinstance(domain_config, dict):
        raw_domain_name = domain_config.get("name")
        if isinstance(raw_domain_name, str) and raw_domain_name.strip():
            domain_name = raw_domain_name.strip()
        else:
            logger.warning("Invalid or missing domain_config['name']; using fallback '%s'", domain_name)
    else:
        logger.warning("domain_config is not a dict; using fallback '%s'", domain_name)

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("DUAL-LENS ANALYSIS REPORT\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Domain: {domain_name}\n")
        f.write(f"Overlays: {', '.join(overlay_ids)}\n")
        f.write(f"Total Events: {len(events)}\n")
        f.write(f"Total Entities: {len(filtered_entities)}\n\n")

        for overlay_id in overlay_ids:
            f.write("=" * 70 + "\n")
            f.write(f"TOP 20 ENTITIES - {overlay_id.upper()}\n")
            f.write("=" * 70 + "\n\n")

            sorted_entities = sorted(
                (e for e in filtered_entities if entity_scores.get(e.get("entity_id"), {}).get(overlay_id)),
                key=lambda e: entity_scores.get(e.get("entity_id"), {}).get(overlay_id, {}).get("score", float("-inf")),
                reverse=True,
            )

            for i, entity in enumerate(sorted_entities[:20], 1):
                entity_id = entity.get("entity_id")
                if not entity_id:
                    continue
                scores = entity_scores.get(entity_id, {}).get(overlay_id, {})
                event_count = len(entity_events.get(entity_id, []))

                f.write(f"{i:2d}. {entity.get('entity_name',''):30s} ")
                f.write(f"({entity.get('entity_type',''):12s}) ")
                f.write(f"Score: {scores.get('score', 0):6.2f} ")
                f.write(f"[{scores.get('bucket',''):15s}] ")
                f.write(f"Events: {event_count:3d}\n")

            f.write("\n")

        f.write("=" * 70 + "\n")
        f.write("BUCKET DISTRIBUTION\n")
        f.write("=" * 70 + "\n\n")

        if not overlay_ids:
            logger.warning("No overlays configured; bucket distribution is empty")
            f.write("No bucket data available (no overlays configured).\n")

        for overlay_id in overlay_ids:
            f.write(f"{overlay_id}:\n")

            bucket_counts = defaultdict(int)
            for entity in filtered_entities:
                entity_id = entity.get("entity_id")
                if not entity_id:
                    continue
                overlay_scores = entity_scores.get(entity_id, {}).get(overlay_id)
                if overlay_scores and "bucket" in overlay_scores:
                    bucket = overlay_scores["bucket"]
                    bucket_counts[bucket] += 1
            total = sum(bucket_counts.values())
            for bucket in [
                "strong",
                "promising",
                "exploratory",
                "stalled",
                "deprioritized",
            ]:
                count = bucket_counts.get(bucket, 0)
                pct = (count / total * 100) if total else 0
                f.write(f"  {bucket:15s}: {count:4d} ({pct:5.1f}%)\n")
            if not bucket_counts:
                logger.warning("No bucket data available for overlay '%s'", overlay_id)
                f.write("  No bucket data available\n")
            f.write("\n")
