# Search Query Expansion Plan

## Goals
- Introduce a query-understanding layer that expands user queries with synonyms, stems, and optional LLM rewrites to improve recall without harming precision.
- Provide an evaluation harness measuring retrieval quality (precision@k, recall@k) against curated fixtures and run within CI.
- Document configuration, operational toggles, and observability expectations for the expansion pipeline.
- Keep overall coverage ≥80%; new modules ≥90%.

## Implementation Tasks
1. Expansion engine
   - ✅ Build a modular pipeline supporting:
     * rule-based stemming/lemmatization,
     * synonym lookup (WordNet/custom dictionaries),
     * optional LLM-based reformulation hook.
   - ✅ Allow per-tenant/agent configuration with sensible defaults and guardrails on expansion fan-out.
2. Search integration
   - ✅ Update query entrypoints so expanded queries feed into existing fulltext/semantic/hybrid flows without infinite loops.
   - ✅ Record expansion metadata on responses (original query, applied transforms, expansion cost).
3. Evaluation harness
   - ✅ Create a fixture dataset mapping queries to relevant memory IDs.
   - ✅ Add CLI/pytest command to compare baseline vs. expanded retrieval (precision@k / recall@k, aggregated deltas).
   - 🔄 Monitor results in CI and adjust thresholds once real datasets are curated.
4. Observability
   - ✅ Emit structured logs and optional metrics capturing expansion steps, synonym sources, and LLM latency/failures.
   - ✅ Provide toggles to disable expansion when providers unavailable.
5. Documentation
   - ✅ Update README/runbooks with configuration instructions, evaluation workflow, and troubleshooting tips.

## Testing Strategy
- ✅ Unit tests for expansion rules, ensuring deterministic output and bounded expansions.
- ✅ Integration tests demonstrating improved recall on the fixture dataset while maintaining precision.
- ✅ Tests covering failure paths (LLM provider disabled, synonym source missing) and verifying graceful fallback.
- ✅ Evaluation harness tests verifying metric calculations and CLI output.
- 🔄 Full pytest run with coverage enforcement (monitor for new datasets as they grow).

## Dependencies & Risks
- Builds on hybrid ranking improvements for final ordering.
- LLM-based expansion introduces latency and potential cost; add caching and rate limiting.
- Expansion must respect scope/visibility constraints; ensure filters applied post-expansion.
- Synonym dictionaries require maintenance; document contribution workflow.
