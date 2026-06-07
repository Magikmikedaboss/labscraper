import sqlite3
import logging
from collections import defaultdict
from contextlib import closing
from typing import Any, Mapping, Sequence, Tuple


logger = logging.getLogger(__name__)

SCORE_SCALE_FACTOR = 2  # SCORE_SCALE_FACTOR is set to 2 so each event adds roughly 2 scoring points, which keeps score growth sensitive without overreacting to noise.
MIN_SCORE_THRESHOLD = 10  # MIN_SCORE_THRESHOLD is set to 10 to avoid very low max scores for rare entities and to compress low-frequency buckets less aggressively.

RowLike = Mapping[str, Any]
RowSeq = Sequence[RowLike]


def load_events_and_entities(db_path: str) -> Tuple[RowSeq, RowSeq, RowSeq, RowSeq]:
    try:
        with closing(sqlite3.connect(db_path)) as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()

            events = cur.execute(
                """
                SELECT event_id, event_type, stage, confidence, evidence_snippet,
                       source_id, doc_id, chunk_id, page_number, created_at
                FROM research_events
                """
            ).fetchall()
            entities = cur.execute(
                """
                SELECT entity_id, entity_type, entity_name, entity_variant, organism, created_at
                FROM entities
                """
            ).fetchall()
            event_entities = cur.execute(
                "SELECT entity_id, event_id FROM event_entities"
            ).fetchall()
            model_rows = cur.execute(
                """
                SELECT ee.event_id, e.entity_name
                FROM event_entities ee
                JOIN entities e ON ee.entity_id = e.entity_id
                WHERE e.entity_type = 'model'
                """
            ).fetchall()
    except sqlite3.Error as e:
        logger.error("Failed loading events/entities from %s: %s", db_path, e)
        raise

    return events, entities, event_entities, model_rows

def build_event_overlay_scores(events: Sequence[RowLike], scorer: Any) -> dict[str, dict[str, float]]:
    event_overlay_scores = {}

    for event in events:
        event_dict = dict(event)
        scores = scorer.apply_event_scores(event_dict)
        event_id = event_dict.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            logger.warning("Skipping event without valid event_id in overlay scoring: %r", event_dict)
            continue
        event_overlay_scores[event_id] = scores

    return event_overlay_scores

def build_entity_event_map(
    event_entities: Sequence[RowLike],
    entity_id_mapping: Mapping[str, str],
) -> dict[str, list[str]]:
    entity_events = defaultdict(list)

    for row in event_entities:
        row_dict = dict(row) if not isinstance(row, dict) else row
        entity_id = row_dict.get("entity_id")
        event_id = row_dict.get("event_id")
        if entity_id is None or event_id is None:
            continue
        if not isinstance(entity_id, str) or not isinstance(event_id, str):
            continue

        canonical_id = entity_id_mapping.get(entity_id, entity_id)
        if not isinstance(canonical_id, str) or not canonical_id:
            continue
        entity_events[canonical_id].append(event_id)

    return entity_events

def build_event_models(model_rows):
    event_models = defaultdict(set)

    for row in model_rows:
        row_dict = dict(row) if not isinstance(row, dict) else row
        event_id = row_dict.get("event_id")
        entity_name = row_dict.get("entity_name")
        if not isinstance(event_id, str) or not isinstance(entity_name, str):
            continue
        event_id = event_id.strip()
        entity_name = entity_name.strip()
        if not event_id or not entity_name:
            continue
        event_models[event_id].add(entity_name)

    return event_models

def build_entity_models_map(entity_events, event_models):
    entity_models_map = defaultdict(set)

    for entity_id, event_ids in entity_events.items():
        for event_id in event_ids:
            entity_models_map[entity_id].update(event_models.get(event_id, set()))

    return entity_models_map

def build_entity_scores(
    entities,
    overlay_ids,
    entity_events,
    entity_models_map,
    event_overlay_scores,
    scorer,
):
    entity_scores = {}

    for entity in entities:
        if isinstance(entity, sqlite3.Row):
            entity = dict(entity)
        elif not isinstance(entity, dict):
            logger.warning("Skipping malformed entity (not a dict): %r", entity)
            continue

        entity_id = entity.get("entity_id")
        if not isinstance(entity_id, str) or not entity_id:
            logger.warning("Skipping malformed entity without valid entity_id: %r", entity)
            continue

        event_ids = entity_events.get(entity_id, [])
        models_list = list(entity_models_map.get(entity_id, set()))
        entity_scores[entity_id] = {}

        for overlay_id in overlay_ids:
            event_scores_list = [
                event_overlay_scores.get(event_id, {}).get(overlay_id, 0)
                for event_id in event_ids
            ]

            entity_dict = dict(entity)
            entity_dict["event_count"] = len(event_ids)

            final_score = scorer.calculate_entity_score(
                entity_dict,
                event_scores_list,
                overlay_id,
                entity_models=models_list,
            )

            # Scale max_score by event count, cap extreme values, and enforce a minimum threshold for rare entities.
            capped_score = min(len(event_ids) * SCORE_SCALE_FACTOR, 10000)
            max_score = max(capped_score, MIN_SCORE_THRESHOLD)
            bucket = scorer.bucket_score(final_score, max_score)

            entity_scores[entity_id][overlay_id] = {
                "score": final_score,
                "bucket": bucket,
            }

    return entity_scores
