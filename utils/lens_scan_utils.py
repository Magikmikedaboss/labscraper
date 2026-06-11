from __future__ import annotations

import logging
import os
from pathlib import Path


def _env_limit(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    trimmed_value = value.strip()
    try:
        return int(trimmed_value)
    except ValueError as exc:
        raise ValueError(f"Environment variable '{name}' has non-integer value: '{trimmed_value}'") from exc


def _configure_logging(logger: logging.Logger, out_dir: Path, log_filename: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    log_path = out_dir / log_filename

    has_file_handler = any(
        isinstance(handler, logging.FileHandler)
        and Path(getattr(handler, "baseFilename", "")).resolve() == log_path.resolve()
        for handler in logger.handlers
    )
    if not has_file_handler:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    has_stream_handler = any(type(handler) is logging.StreamHandler for handler in logger.handlers)
    if not has_stream_handler:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)