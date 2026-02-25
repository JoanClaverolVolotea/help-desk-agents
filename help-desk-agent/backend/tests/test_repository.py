from __future__ import annotations

from backend.domain.templates import seed_category_definitions, seed_use_case_definitions
from backend.storage import CategoryRepository, UseCaseRepository


def test_repository_create_update_publish_keeps_version_sequence(tmp_path) -> None:
    db_path = tmp_path / "repo.db"
    category_repository = CategoryRepository(db_path=db_path)
    use_case_repository = UseCaseRepository(db_path=db_path)
    category_repository.initialize()
    use_case_repository.initialize()

    category_definition = seed_category_definitions()[0][1]
    category = category_repository.create_category_with_draft(
        slug="access-reset",
        draft_definition=category_definition,
    )
    assert category.draft_version_number == 1

    category = category_repository.publish_draft(category.category_id)
    assert category.published_version_number == 1

    use_case_definition = seed_use_case_definitions()[0].definition
    created = use_case_repository.create_use_case_with_draft(
        slug="reset-access-sequence",
        category_id=category.category_id,
        category_version_number=category.published_version_number or 1,
        draft_definition=use_case_definition,
    )
    assert created.draft_version_number == 1
    assert created.published_version_number is None

    published = use_case_repository.publish_draft(created.use_case_id)
    assert published.published_version_number == 1

    updated_definition = use_case_definition.model_copy(update={"display_name": "Reset Access v2"})
    updated = use_case_repository.update_draft(
        created.use_case_id,
        category_id=category.category_id,
        category_version_number=category.published_version_number or 1,
        draft_definition=updated_definition,
    )
    assert updated.draft_version_number == 2
    assert updated.published_version_number == 1

    published_v2 = use_case_repository.publish_draft(created.use_case_id)
    assert published_v2.published_version_number == 2
    assert published_v2.display_name == "Reset Access v2"


def test_category_archive_detaches_linked_use_cases(tmp_path) -> None:
    db_path = tmp_path / "detach.db"
    category_repository = CategoryRepository(db_path=db_path)
    use_case_repository = UseCaseRepository(db_path=db_path)
    category_repository.initialize()
    use_case_repository.initialize()

    category_definition = seed_category_definitions()[0][1]
    category = category_repository.create_category_with_draft(
        slug="detach-access",
        draft_definition=category_definition,
    )
    category = category_repository.publish_draft(category.category_id)

    use_case_definition = seed_use_case_definitions()[0].definition
    use_case = use_case_repository.create_use_case_with_draft(
        slug="detach-case",
        category_id=category.category_id,
        category_version_number=category.published_version_number or 1,
        draft_definition=use_case_definition,
    )
    use_case_repository.publish_draft(use_case.use_case_id)

    category_repository.archive_category(category.category_id)

    detached = use_case_repository.get_use_case_detail(use_case.use_case_id, include_archived=True)
    assert detached.category_id is None
    assert detached.category_version_number is None
    assert detached.is_detached is True


def test_use_case_archive_and_restore(tmp_path) -> None:
    db_path = tmp_path / "archive.db"
    category_repository = CategoryRepository(db_path=db_path)
    use_case_repository = UseCaseRepository(db_path=db_path)
    category_repository.initialize()
    use_case_repository.initialize()

    category_definition = seed_category_definitions()[0][1]
    category = category_repository.create_category_with_draft(
        slug="archive-access",
        draft_definition=category_definition,
    )
    category = category_repository.publish_draft(category.category_id)

    use_case_definition = seed_use_case_definitions()[0].definition
    use_case = use_case_repository.create_use_case_with_draft(
        slug="archive-case",
        category_id=category.category_id,
        category_version_number=category.published_version_number or 1,
        draft_definition=use_case_definition,
    )

    archived = use_case_repository.archive_use_case(use_case.use_case_id)
    assert archived.archived is True

    restored = use_case_repository.restore_use_case(use_case.use_case_id)
    assert restored.archived is False


def test_sync_default_use_case_for_published_category(tmp_path) -> None:
    db_path = tmp_path / "default-sync.db"
    category_repository = CategoryRepository(db_path=db_path)
    use_case_repository = UseCaseRepository(db_path=db_path)
    category_repository.initialize()
    use_case_repository.initialize()

    category_definition = seed_category_definitions()[0][1]
    category = category_repository.create_category_with_draft(
        slug="default-sync-category",
        draft_definition=category_definition,
    )
    category = category_repository.publish_draft(category.category_id)

    first_sync = use_case_repository.sync_default_use_cases_for_published_categories(
        category_repository
    )
    assert len(first_sync) == 1
    assert first_sync[0].is_system_default is True
    assert first_sync[0].category_id == category.category_id
    assert first_sync[0].published_version_number == 1

    second_sync = use_case_repository.sync_default_use_cases_for_published_categories(
        category_repository
    )
    assert len(second_sync) == 1
    assert second_sync[0].use_case_id == first_sync[0].use_case_id
    assert second_sync[0].published_version_number == first_sync[0].published_version_number


def test_category_archive_and_restore_handles_system_default(tmp_path) -> None:
    db_path = tmp_path / "default-archive-restore.db"
    category_repository = CategoryRepository(db_path=db_path)
    use_case_repository = UseCaseRepository(db_path=db_path)
    category_repository.initialize()
    use_case_repository.initialize()

    category_definition = seed_category_definitions()[0][1]
    category = category_repository.create_category_with_draft(
        slug="default-lifecycle-category",
        draft_definition=category_definition,
    )
    category = category_repository.publish_draft(category.category_id)

    manual_definition = seed_use_case_definitions()[0].definition
    manual_use_case = use_case_repository.create_use_case_with_draft(
        slug="manual-lifecycle-case",
        category_id=category.category_id,
        category_version_number=category.published_version_number or 1,
        draft_definition=manual_definition,
    )
    use_case_repository.publish_draft(manual_use_case.use_case_id)

    default_use_case = use_case_repository.create_or_update_default_use_case_for_category(category)
    assert default_use_case.is_system_default is True
    assert default_use_case.archived is False

    category_repository.archive_category(category.category_id)
    archived_default = use_case_repository.archive_default_use_case_for_category(
        category.category_id
    )
    assert archived_default is not None
    assert archived_default.archived is True

    detached_manual = use_case_repository.get_use_case_detail(
        manual_use_case.use_case_id,
        include_archived=True,
    )
    assert detached_manual.is_detached is True
    assert detached_manual.archived is False

    restored_category = category_repository.restore_category(category.category_id)
    restored_default = use_case_repository.create_or_update_default_use_case_for_category(
        restored_category
    )
    assert restored_default.archived is False
    assert restored_default.is_system_default is True
    assert restored_default.category_id == category.category_id
