"""
workers/scoring_tasks.py — Async quality scoring tasks

Quality scoring runs after generation completes, not inline.
This keeps the generation stream fast and scoring happens in the background.
"""
from __future__ import annotations

import logging

from workers.celery_app import celery_app

logger = logging.getLogger("ai-site-gen")


@celery_app.task(
    name="workers.scoring_tasks.score_project_version",
    queue="scoring",
    max_retries=2,
    bind=True,
)
def score_project_version(self, version_id: int) -> dict:
    """
    Run quality scoring on a saved project version.
    Scores: HTML, Accessibility, SEO, Security, Performance, Best Practices.
    Results stored back to project_versions.metadata_json.
    
    Phase 2: Scaffolded — full implementation when QualityScorer is built.
    """
    try:
        logger.info(f"Scoring version {version_id} — placeholder")
        # TODO: Phase 2 Stage 4 — wire to ValidatorChain.validate()
        return {"version_id": version_id, "status": "pending_implementation"}
    except Exception as exc:
        logger.error(f"Scoring task failed for version {version_id}: {exc}")
        raise self.retry(exc=exc)
