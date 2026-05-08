"""
XGBoost model training pipeline for Zentro Leads.

Entry points:
  train_scoring_model(db, model_type) — async, trains and saves a model
  count_new_feedback(db)              — async, count labelled feedback rows

Both async functions hand off all sync CPU work to asyncio.to_thread so
they never block the FastAPI event loop.

Training data source:
  ZLScoringFeedback joined → ZLLead
  Labels: feedback.converted (True=1, False=0)
  Features: extracted from ZLLead.score_breakdown + original_score
  (avoids heavy person/company/ICP joins; uses pre-computed sub-scores)

Minimum training data: 50 labelled records (configurable via MODEL_RETRAIN_THRESHOLD).
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import ZLLead, ZLScoringFeedback
from app.scoring.features import extract_features_from_breakdown

MIN_SAMPLES = 50  # Hard floor — below this XGBoost won't generalise


# ── Database helpers ───────────────────────────────────────────────────────────

async def count_new_feedback(db: AsyncSession) -> int:
    """
    Return total number of labelled feedback records available for training.

    Both positive (converted=True) and negative (converted=False) records
    are counted, as XGBoost needs both classes.
    """
    result = await db.execute(
        select(func.count()).select_from(ZLScoringFeedback)
    )
    return int(result.scalar_one() or 0)


async def _load_training_rows(
    db: AsyncSession,
    model_type: str,
    limit: int = 5000,
) -> list[dict[str, Any]]:
    """
    Load feedback + lead rows for the given model_type.

    Returns a list of dicts with keys:
      converted, original_score, score_breakdown, lead_type
    """
    stmt = (
        select(
            ZLScoringFeedback.converted,
            ZLScoringFeedback.original_score,
            ZLLead.score_breakdown,
            ZLLead.lead_type,
        )
        .join(ZLLead, ZLLead.id == ZLScoringFeedback.lead_id)
        .where(ZLLead.lead_type == model_type)
        .where(ZLScoringFeedback.converted.isnot(None))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "converted":       int(row.converted or 0),
            "original_score":  int(row.original_score or 0),
            "score_breakdown": dict(row.score_breakdown or {}),
            "lead_type":       row.lead_type or model_type,
        }
        for row in rows
    ]


# ── Sync training worker (runs in a thread) ────────────────────────────────────

def _train_sync(
    rows: list[dict[str, Any]],
    model_type: str,
) -> dict[str, Any]:
    """
    Synchronous CPU-bound training — called via asyncio.to_thread.

    Returns:
        {
          "auc":     float,
          "samples": int,
          "model_path": str,
          "run_id":  str,
        }
    Raises:
        ValueError if insufficient labelled data.
        RuntimeError on any training failure.
    """
    import pandas as pd
    import xgboost as xgb
    import mlflow
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score

    if len(rows) < MIN_SAMPLES:
        raise ValueError(
            f"Insufficient training data: {len(rows)} rows "
            f"(minimum {MIN_SAMPLES} required)"
        )

    # ── Build feature DataFrame ───────────────────────────────────────────────
    records: list[dict[str, Any]] = []
    labels:  list[int] = []
    for row in rows:
        features = extract_features_from_breakdown(
            breakdown=row["score_breakdown"],
            lead_type=row["lead_type"],
            original_score=row["original_score"],
        )
        records.append(features)
        labels.append(row["converted"])

    X = pd.DataFrame(records)
    y = pd.Series(labels, dtype=int)

    # Drop rows with all-zero features (corrupted breakdown)
    X = X[X.sum(axis=1) > 0]
    y = y[X.index]

    if len(X) < MIN_SAMPLES:
        raise ValueError(
            f"Too few valid feature rows after cleanup: {len(X)}"
        )

    # ── Train / test split ────────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    # ── Class imbalance weight ────────────────────────────────────────────────
    pos_count = max(int(y_train.sum()), 1)
    neg_count = max(len(y_train) - pos_count, 1)
    scale_pos = neg_count / pos_count

    # ── MLflow tracking ───────────────────────────────────────────────────────
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    mlflow.set_experiment("zentro_lead_scoring")

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    run_id   = ""

    with mlflow.start_run(run_name=f"zentro_{model_type}_{date_str}") as run:
        run_id = run.info.run_id

        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            scale_pos_weight=scale_pos,
            random_state=42,
            eval_metric="auc",
            use_label_encoder=False,
            verbosity=0,
        )
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        # ── Evaluate ─────────────────────────────────────────────────────────
        if len(y_test.unique()) < 2:
            # Only one class in test set — AUC undefined, use train accuracy
            auc = float(model.score(X_train, y_train))
            logger.warning(f"[trainer] Test set has only one class — using train accuracy as AUC proxy")
        else:
            proba  = model.predict_proba(X_test)[:, 1]
            auc    = float(roc_auc_score(y_test, proba))

        accuracy = float(model.score(X_test, y_test))

        mlflow.log_params({
            "model_type":       model_type,
            "n_estimators":     100,
            "max_depth":        4,
            "learning_rate":    0.1,
            "scale_pos_weight": round(scale_pos, 3),
            "training_samples": len(X),
            "positive_samples": int(y.sum()),
        })
        mlflow.log_metrics({
            "auc":              auc,
            "accuracy":         accuracy,
            "train_samples":    len(X_train),
            "test_samples":     len(X_test),
        })

        # ── Save model ────────────────────────────────────────────────────────
        os.makedirs("models", exist_ok=True)
        model_path = f"models/{model_type}_scorer.json"
        model.save_model(model_path)
        mlflow.log_artifact(model_path)

        logger.info(
            f"[trainer] {model_type.upper()} model saved: "
            f"AUC={auc:.3f} accuracy={accuracy:.3f} samples={len(X)}"
        )

    return {
        "auc":        auc,
        "accuracy":   accuracy,
        "samples":    len(X),
        "model_path": model_path,
        "run_id":     run_id,
    }


# ── Public async entry point ───────────────────────────────────────────────────

async def train_scoring_model(
    db: AsyncSession,
    model_type: str = "b2b",
) -> dict[str, Any] | None:
    """
    Load training data from the DB and train an XGBoost scoring model.

    Args:
        db:         Active async SQLAlchemy session.
        model_type: "b2b" | "b2c"

    Returns:
        Dict with auc, accuracy, samples, model_path, run_id — or None
        if there's insufficient data to train.
    """
    model_type = model_type.lower()
    logger.info(f"[trainer] Starting {model_type.upper()} model training")

    rows = await _load_training_rows(db, model_type)
    logger.info(f"[trainer] Loaded {len(rows)} feedback rows for '{model_type}'")

    if len(rows) < MIN_SAMPLES:
        logger.warning(
            f"[trainer] Skipping {model_type.upper()} — only {len(rows)} rows "
            f"(need {MIN_SAMPLES})"
        )
        return None

    try:
        result = await asyncio.to_thread(_train_sync, rows, model_type)
        return result
    except ValueError as exc:
        logger.warning(f"[trainer] Training skipped: {exc}")
        return None
    except Exception as exc:
        logger.error(f"[trainer] Training failed for '{model_type}': {exc}")
        raise
