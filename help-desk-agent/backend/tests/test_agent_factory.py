from __future__ import annotations

from agent_runtime.snapshot import build_runtime_snapshot
from models import PublishedUseCaseSummary, UseCaseDefinitionPublished
from templates import seed_use_case_definitions


def _to_published_summary(
    use_case_id: str,
    slug: str,
    category_id: str,
    definition_source,
) -> PublishedUseCaseSummary:
    published_definition = UseCaseDefinitionPublished(
        version_number=1,
        **definition_source.model_dump(),
    )
    return PublishedUseCaseSummary(
        use_case_id=use_case_id,
        slug=slug,
        display_name=definition_source.display_name,
        category_id=category_id,
        category_version_number=1,
        version_number=1,
        definition=published_definition,
    )


def test_agent_factory_builds_specialists_from_published_cases() -> None:
    seeded = seed_use_case_definitions()
    use_cases = [
        _to_published_summary("uc1", "reset-access", "cat-1", seeded[0].definition),
        _to_published_summary("uc2", "alta-onboarding", "cat-2", seeded[1].definition),
    ]

    snapshot = build_runtime_snapshot(use_cases)

    assert snapshot.published_use_cases
    assert len(snapshot.specialists_by_use_case_id) == 2
    assert len(snapshot.triage_agent.handoffs) == 2

    for specialist in snapshot.specialists_by_use_case_id.values():
        assert specialist.tools
        assert len(specialist.tools) == 1
