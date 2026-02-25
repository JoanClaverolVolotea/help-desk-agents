from __future__ import annotations

from repository import CategoryRepository, UseCaseRepository
from templates import seed_category_definitions, seed_use_case_definitions

from agent_runtime.snapshot import RuntimeSnapshot, build_runtime_snapshot


def initialize_repositories(
    category_repository: CategoryRepository,
    use_case_repository: UseCaseRepository,
) -> None:
    category_repository.initialize()
    use_case_repository.initialize()

    categories_by_slug = category_repository.seed_if_empty(seed_category_definitions())
    use_case_repository.seed_if_empty(seed_use_case_definitions(), categories_by_slug)
    use_case_repository.sync_default_use_cases_for_published_categories(category_repository)


def build_snapshot_from_repository(use_case_repository: UseCaseRepository) -> RuntimeSnapshot:
    published_use_cases = use_case_repository.list_published_use_cases()
    return build_runtime_snapshot(published_use_cases)
