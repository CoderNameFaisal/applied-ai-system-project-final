"""Logging setup for PawPal."""

from __future__ import annotations

import logging

from pawpal.config import load_settings


def get_logger(name: str = "pawpal") -> logging.Logger:
    settings = load_settings()
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(settings.log_level)
    return logger


def truncate_text(value: str, max_len: int = 400) -> str:
    if len(value) <= max_len:
        return value
    return value[:max_len] + "...<truncated>"

