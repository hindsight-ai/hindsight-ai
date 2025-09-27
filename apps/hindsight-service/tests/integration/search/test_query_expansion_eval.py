import json
import uuid

from core.search.evaluation import evaluate_cases, load_cases_from_file
from core.db import models


def _create_agent(client):
    response = client.post(
        "/agents/",
        json={"agent_name": "ExpansionAgent", "visibility_scope": "personal"},
        headers={"x-auth-request-email": "expander@example.com", "x-auth-request-user": "Expander"},
    )
    assert response.status_code == 201, response.text
    return response.json()["agent_id"]


def _ensure_user(client):
    client.get("/keywords/", headers={"x-auth-request-email": "expander@example.com", "x-auth-request-user": "Expander"})


def test_query_expansion_evaluation_improves_recall(db_session, client, tmp_path):
    _ensure_user(client)
    agent_id = _create_agent(client)

    # Create a memory block containing "performance" which should be surfaced when querying for "speed".
    response = client.post(
        "/memory-blocks/",
        json={
            "agent_id": agent_id,
            "conversation_id": str(uuid.uuid4()),
            "content": "System performance tuning notes",
            "visibility_scope": "personal",
        },
        headers={"x-auth-request-email": "expander@example.com", "x-auth-request-user": "Expander"},
    )
    assert response.status_code == 201, response.text
    memory_id = response.json()["id"]

    dataset = [{"query": "speed", "search_type": "hybrid", "relevant_ids": [memory_id]}]
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")

    user = db_session.query(models.User).filter(models.User.email == "expander@example.com").one()
    current_user = {
        "id": user.id,
        "is_superadmin": bool(user.is_superadmin),
        "memberships": [],
        "memberships_by_org": {},
    }

    cases = load_cases_from_file(str(dataset_path))
    summary = evaluate_cases(db_session, cases, current_user=current_user)

    case_summary = summary["cases"][0]
    assert case_summary["expansion_metadata"]["expansion"]["expansion_applied"] is True
    # Debugging aid: ensure at least one expanded query produced results
    assert case_summary["expansion_metadata"]["expansion"]["expanded_queries"], "expected expanded queries"

    assert summary["baseline"]["recall"] < summary["expanded"]["recall"], (
        f"Expected improved recall; case summary: {case_summary}"
    )
