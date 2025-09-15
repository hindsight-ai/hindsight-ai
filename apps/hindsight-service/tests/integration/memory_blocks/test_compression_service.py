import uuid
from sqlalchemy.orm import Session
from core.pruning.compression_service import CompressionService
from core.db import models
import sys
import types



def test_compression_service_no_api_key_returns_error(db_session: Session):
    # Create agent and memory block
    agent_id = uuid.uuid4()
    # assign owner to satisfy personal-owner DB constraint
    owner = models.User(email=f"cmp_owner_{uuid.uuid4().hex}@example.com", display_name="CmpOwner")
    db_session.add(owner)
    db_session.flush()
    agent = models.Agent(agent_id=agent_id, agent_name="Compress Agent", owner_user_id=owner.id)
    db_session.add(agent)
    mb = models.MemoryBlock(
        id=uuid.uuid4(),
        agent_id=agent_id,
        conversation_id=uuid.uuid4(),
        content="Some detailed content about system performance and latency issues.",
        lessons_learned="Monitor query plans and add proper indexes",
        visibility_scope="personal",
        owner_user_id=owner.id,
    )
    db_session.add(mb)
    db_session.commit()

    service = CompressionService(llm_api_key=None)  # Force missing key path
    result = service.compress_memory_block(db_session, mb.id)
    assert "error" in result
    assert result["error"] == "LLM service not available"
    assert "message" in result


def test_compression_prompt_generation_structure(db_session: Session):
    agent_id = uuid.uuid4()
    owner = models.User(email=f"prompt_owner_{uuid.uuid4().hex}@example.com", display_name="PromptOwner")
    db_session.add(owner)
    db_session.flush()
    agent = models.Agent(agent_id=agent_id, agent_name="Prompt Agent", owner_user_id=owner.id)
    db_session.add(agent)
    mb = models.MemoryBlock(
        id=uuid.uuid4(),
        agent_id=agent_id,
        conversation_id=uuid.uuid4(),
        content="Original content with multiple ideas and insights for compression.",
        lessons_learned="We learned that batching improves throughput",
        visibility_scope="personal",
        owner_user_id=owner.id,
    )
    db_session.add(mb)
    db_session.commit()

    service = CompressionService(llm_api_key="dummy")  # Won't actually call because google lib likely absent
    prompt = service._create_compression_prompt(mb)  # Access internal for deterministic test
    # Basic structural assertions
    assert "COMPRESS" in prompt.upper()
    assert "ORIGINAL CONTENT" in prompt
    assert str(mb.id) in prompt
    assert "compressed_content" in prompt


def _install_mock_gemini(success: bool = True, malformed: bool = False, shorter_factor: float = 0.4):
    """Install a mocked google.genai module in sys.modules.

    Args:
        success: whether to return a successful JSON structure
        malformed: if True, return invalid JSON (overrides success)
        shorter_factor: factor to shrink original content lengths
    """
    google_mod = types.ModuleType("google")
    google_mod.__path__ = []  # mark as package
    genai_mod = types.ModuleType("google.genai")

    class DummyResponse:
        def __init__(self, text: str):
            self.text = text

    class DummyModels:
        def __init__(self, make_text):
            self._make_text = make_text

        def generate_content(self, model, contents, config):  # noqa: D401
            return DummyResponse(self._make_text(contents))

    class DummyClient:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.models = DummyModels(gen_text)

    def gen_text(prompt: str) -> str:  # prompt available if needed
        if malformed:
            return "NOT_JSON"
        if not success:
            # Provide JSON that leads to actual_ratio >= 1 to simulate failure not used here
            return '{"compressed_content": "same", "compressed_lessons_learned": "same", "compression_ratio": 1, "key_insights_preserved": [], "compression_quality_score": 5, "rationale": "no change"}'
        # For success path we produce shorter content markers
        data = {
            "compressed_content": "SHORT_CONTENT"[:int(12 * shorter_factor)] or "X",
            "compressed_lessons_learned": "SHORT_LESSONS"[:int(13 * shorter_factor)] or "Y",
            "compression_ratio": shorter_factor,
            "key_insights_preserved": ["insight A", "insight B"],
            "compression_quality_score": 8,
            "rationale": "Removed redundancy while preserving key insights"
        }
        return json_dumps(data)

    def json_dumps(d):
        import json as _json
        return _json.dumps(d)

    genai_mod.Client = DummyClient
    sys.modules["google"] = google_mod
    sys.modules["google.genai"] = genai_mod


def test_compression_success_path(db_session: Session):
    # Arrange original memory block
    agent_id = uuid.uuid4()
    owner = models.User(email=f"succ_owner_{uuid.uuid4().hex}@example.com", display_name="SuccOwner")
    db_session.add(owner)
    db_session.flush()
    agent = models.Agent(agent_id=agent_id, agent_name="Success Agent", owner_user_id=owner.id)
    db_session.add(agent)
    content = "This is the original verbose content with many repeated details." * 2
    lessons = "Original lessons learned include optimizing queries and caching." * 2
    mb = models.MemoryBlock(
        id=uuid.uuid4(),
        agent_id=agent_id,
        conversation_id=uuid.uuid4(),
        content=content,
        lessons_learned=lessons,
        visibility_scope="personal",
        owner_user_id=owner.id,
    )
    db_session.add(mb)
    db_session.commit()

    # Mock LLM
    _install_mock_gemini(success=True, malformed=False, shorter_factor=0.3)
    service = CompressionService(llm_api_key="dummy-key")
    result = service.compress_memory_block(db_session, mb.id)

    assert "error" not in result, f"Unexpected error: {result}"
    assert result["memory_id"] == str(mb.id)
    assert result["compressed_content"]
    assert result["compressed_lessons_learned"]
    assert 0 < result["compression_ratio"] < 1
    # Ensure actually shorter
    original_len = len(content) + len(lessons)
    compressed_len = len(result["compressed_content"]) + len(result["compressed_lessons_learned"])
    assert compressed_len < original_len
    assert isinstance(result["key_insights_preserved"], list)
    assert "timestamp" in result


def test_compression_parse_failure_returns_error(db_session: Session):
    agent_id = uuid.uuid4()
    owner = models.User(email=f"parse_owner_{uuid.uuid4().hex}@example.com", display_name="ParseOwner")
    db_session.add(owner)
    db_session.flush()
    agent = models.Agent(agent_id=agent_id, agent_name="Parse Agent", owner_user_id=owner.id)
    db_session.add(agent)
    mb = models.MemoryBlock(
        id=uuid.uuid4(),
        agent_id=agent_id,
        conversation_id=uuid.uuid4(),
        content="Content to trigger parse failure",
        lessons_learned="Lessons here",
        visibility_scope="personal",
        owner_user_id=owner.id,
    )
    db_session.add(mb)
    db_session.commit()

    _install_mock_gemini(success=True, malformed=True)
    service = CompressionService(llm_api_key="dummy-key")
    result = service.compress_memory_block(db_session, mb.id)
    assert result.get("error") == "LLM response parsing failed"
    assert "message" in result
