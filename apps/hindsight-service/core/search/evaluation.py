"""Utilities to evaluate query expansion effectiveness."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy.orm import Session

from core.db import crud
from core.search import get_search_service


@dataclass
class QueryExpansionCase:
    """Single evaluation case for query expansion."""

    query: str
    search_type: str = "fulltext"
    relevant_ids: Sequence[uuid.UUID] = ()
    limit: int = 10
    include_archived: bool = False
    agent_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "QueryExpansionCase":
        return cls(
            query=str(payload["query"]).strip(),
            search_type=str(payload.get("search_type", "fulltext")),
            relevant_ids=[uuid.UUID(value) for value in payload.get("relevant_ids", [])],
            limit=int(payload.get("limit", 10)),
            include_archived=bool(payload.get("include_archived", False)),
            agent_id=uuid.UUID(payload["agent_id"]) if payload.get("agent_id") else None,
            conversation_id=uuid.UUID(payload["conversation_id"]) if payload.get("conversation_id") else None,
        )


def load_cases_from_file(path: str) -> List[QueryExpansionCase]:
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, list):
        raise ValueError("Query expansion dataset must be a list of cases")
    return [QueryExpansionCase.from_dict(item) for item in payload]


def evaluate_cases(
    db: Session,
    cases: Iterable[QueryExpansionCase],
    *,
    current_user: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute aggregate precision/recall metrics for the supplied cases."""

    search_service = get_search_service()

    per_case: List[Dict[str, Any]] = []
    baseline_metrics: List[Dict[str, float]] = []
    expanded_metrics: List[Dict[str, float]] = []

    for case in cases:
        baseline_results = _run_baseline(search_service, db, case, current_user)
        expanded_results, expansion_metadata = _run_expanded(db, case, current_user)

        baseline_ids = [str(item.id) for item in baseline_results]
        expanded_ids = [str(item.id) for item in expanded_results]
        relevant_ids = [str(rid) for rid in case.relevant_ids]

        baseline_score = _compute_metrics(baseline_ids, relevant_ids)
        expanded_score = _compute_metrics(expanded_ids, relevant_ids)

        baseline_metrics.append(baseline_score)
        expanded_metrics.append(expanded_score)

        per_case.append(
            {
                "query": case.query,
                "search_type": case.search_type,
                "baseline": baseline_score,
                "expanded": expanded_score,
                "expansion_metadata": expansion_metadata,
                "baseline_ids": baseline_ids,
                "expanded_ids": expanded_ids,
            }
        )

    baseline_summary = _aggregate_metrics(baseline_metrics)
    expanded_summary = _aggregate_metrics(expanded_metrics)

    delta = {
        key: expanded_summary.get(key, 0.0) - baseline_summary.get(key, 0.0)
        for key in {"precision", "recall"}
    }

    return {
        "cases": per_case,
        "baseline": baseline_summary,
        "expanded": expanded_summary,
        "delta": delta,
    }


# ---------------------------------------------------------------------------
# Internal helpers


def _run_baseline(search_service, db: Session, case: QueryExpansionCase, current_user: Optional[Dict[str, Any]]):
    search_type = case.search_type.lower()
    kwargs = {
        "db": db,
        "query": case.query,
        "agent_id": case.agent_id,
        "conversation_id": case.conversation_id,
        "limit": case.limit,
        "include_archived": case.include_archived,
        "current_user": current_user,
    }
    if search_type == "semantic":
        return search_service.search_memory_blocks_semantic(
            similarity_threshold=0.7,  # default threshold
            **kwargs,
        )[0]
    if search_type == "hybrid":
        return search_service.search_memory_blocks_hybrid(**kwargs)[0]
    # Default: fulltext
    return search_service.search_memory_blocks_fulltext(
        min_score=0.1,
        **kwargs,
    )[0]


def _run_expanded(db: Session, case: QueryExpansionCase, current_user: Optional[Dict[str, Any]]):
    search_type = case.search_type.lower()
    kwargs = {
        "db": db,
        "query": case.query,
        "agent_id": case.agent_id,
        "conversation_id": case.conversation_id,
        "limit": case.limit,
        "include_archived": case.include_archived,
        "current_user": current_user,
    }
    if search_type == "semantic":
        return crud.search_memory_blocks_semantic(
            similarity_threshold=0.7,
            **kwargs,
        )
    if search_type == "hybrid":
        return crud.search_memory_blocks_hybrid(
            fulltext_weight=0.7,
            semantic_weight=0.3,
            min_combined_score=0.1,
            **kwargs,
        )
    return crud.search_memory_blocks_fulltext(
        min_score=0.1,
        **kwargs,
    )


def _compute_metrics(result_ids: Sequence[str], relevant_ids: Sequence[str]) -> Dict[str, float]:
    relevant_set = set(relevant_ids)
    if not relevant_set:
        # When no ground truth provided, treat as neutral outcome
        return {"precision": 1.0, "recall": 1.0}
    hits = [rid for rid in result_ids if rid in relevant_set]
    precision = len(hits) / len(result_ids) if result_ids else 0.0
    recall = len(hits) / len(relevant_set) if relevant_set else 0.0
    return {
        "precision": precision,
        "recall": recall,
    }


def _aggregate_metrics(metrics: Sequence[Dict[str, float]]) -> Dict[str, float]:
    if not metrics:
        return {"precision": 0.0, "recall": 0.0}
    precision = sum(item.get("precision", 0.0) for item in metrics) / len(metrics)
    recall = sum(item.get("recall", 0.0) for item in metrics) / len(metrics)
    return {"precision": precision, "recall": recall}
