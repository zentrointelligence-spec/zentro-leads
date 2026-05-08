"""
XGBoost model inference for Zentro Leads scoring.

Public API:
  predict_lead_score(features, model_type) → int | None
  load_model(model_type)                   → XGBClassifier | None
  clear_model_cache()                      → None  (call after retrain)

Models are loaded once per process via lru_cache.
A missing model file → returns None → engine falls back to deterministic scoring.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from loguru import logger


@lru_cache(maxsize=4)
def load_model(model_type: str = "b2b"):
    """
    Load an XGBClassifier from disk and cache it in-process.

    Uses a per-model-type path convention: models/{model_type}_scorer.json
    Falls back to settings.XGBOOST_MODEL_PATH for the "b2b" default.

    Returns:
        Loaded XGBClassifier, or None if the model file does not exist.
    """
    import xgboost as xgb
    from app.config import settings

    path = f"models/{model_type}_scorer.json"
    # Honour the config override for the default b2b model
    if model_type == "b2b" and settings.XGBOOST_MODEL_PATH:
        path = settings.XGBOOST_MODEL_PATH

    if not os.path.exists(path):
        logger.debug(
            f"[ml_scorer] Model file not found: '{path}' — "
            f"deterministic engine will be used for '{model_type}'"
        )
        return None

    try:
        model = xgb.XGBClassifier()
        model.load_model(path)
        logger.info(f"[ml_scorer] Loaded {model_type.upper()} model from '{path}'")
        return model
    except Exception as exc:
        logger.error(f"[ml_scorer] Failed to load model '{path}': {exc}")
        return None


def clear_model_cache() -> None:
    """
    Evict all cached models so they are reloaded from disk on next inference.
    Call this immediately after a retrain completes.
    """
    load_model.cache_clear()
    logger.info("[ml_scorer] Model cache cleared — models will reload on next call")


def predict_lead_score(
    features: dict[str, Any],
    model_type: str = "b2b",
) -> int | None:
    """
    Run inference for a single lead and return a 0–100 score.

    Args:
        features:   Feature dict from extract_b2b_features() or
                    extract_b2c_features() or extract_features_from_breakdown().
        model_type: "b2b" | "b2c"

    Returns:
        Integer score 0–100, or None if the model is not available
        (signals the engine to fall back to the deterministic scorer).
    """
    import pandas as pd

    model = load_model(model_type)
    if model is None:
        return None

    if not features:
        logger.debug("[ml_scorer] Empty feature dict — returning None")
        return None

    try:
        X = pd.DataFrame([features])

        # Align columns to the model's expected feature order
        expected_cols = getattr(model, "feature_names_in_", None)
        if expected_cols is not None:
            # Add any missing columns with 0
            for col in expected_cols:
                if col not in X.columns:
                    X[col] = 0.0
            X = X[list(expected_cols)]

        proba = model.predict_proba(X)[0][1]
        score = min(int(round(proba * 100)), 100)
        logger.debug(f"[ml_scorer] {model_type.upper()} ML score: {score} (proba={proba:.4f})")
        return score

    except Exception as exc:
        logger.warning(f"[ml_scorer] Inference failed for '{model_type}': {exc}")
        return None
