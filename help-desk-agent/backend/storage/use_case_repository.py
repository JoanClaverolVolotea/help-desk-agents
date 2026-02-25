from __future__ import annotations

import json
import pathlib
import sqlite3
import uuid
from typing import TYPE_CHECKING

from backend.domain.models import (
    CategoryDetail,
    PublishedUseCaseSummary,
    UseCaseDefinitionDraft,
    UseCaseDefinitionPublished,
    UseCaseDetail,
    UseCaseListItem,
    UseCaseStep,
    VersionStatus,
)
from backend.domain.templates import SeedUseCase

from .db import connect, init_schema, resolve_db_path
from .errors import NoDraftAvailableError, UseCaseNotFoundError
from .sql_helpers import _active_published_row, _editable_draft_row, _next_version_number, _utc_now

if TYPE_CHECKING:
    from .category_repository import CategoryRepository


class UseCaseRepository:
    def __init__(self, db_path: str | pathlib.Path | None = None) -> None:
        if isinstance(db_path, pathlib.Path):
            self.db_path = db_path
        else:
            self.db_path = resolve_db_path(db_path)

    def initialize(self) -> None:
        with connect(self.db_path) as conn:
            init_schema(conn)

    def list_use_cases(self, include_archived: bool = False) -> list[UseCaseListItem]:
        where_clause = "" if include_archived else "WHERE archived = 0"
        query = f"""
            SELECT id, slug, display_name, template_id, category_id, category_version_number,
                   is_system_default,
                   created_at, updated_at, archived
            FROM use_cases
            {where_clause}
            ORDER BY updated_at DESC
        """

        with connect(self.db_path) as conn:
            use_cases = conn.execute(query).fetchall()

            items: list[UseCaseListItem] = []
            for row in use_cases:
                version_rows = self._load_use_case_version_rows(conn, row["id"])
                published_row = _active_published_row(version_rows)
                draft_row = _editable_draft_row(version_rows, published_row)

                category_id = row["category_id"]
                category_version_number = row["category_version_number"]
                is_detached = category_id is None or category_version_number is None

                items.append(
                    UseCaseListItem(
                        use_case_id=row["id"],
                        slug=row["slug"],
                        display_name=row["display_name"],
                        category_id=category_id,
                        category_version_number=category_version_number,
                        is_system_default=bool(row["is_system_default"]),
                        is_detached=is_detached,
                        draft_version_number=draft_row["version_number"] if draft_row else None,
                        published_version_number=(
                            published_row["version_number"] if published_row else None
                        ),
                        archived=bool(row["archived"]),
                        updated_at=row["updated_at"],
                    )
                )
            return items

    def get_use_case_detail(self, use_case_id: str, include_archived: bool = True) -> UseCaseDetail:
        with connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, slug, display_name, template_id, category_id, category_version_number,
                       is_system_default,
                       created_at, updated_at, archived
                FROM use_cases
                WHERE id = ?
                """,
                (use_case_id,),
            ).fetchone()

            if row is None:
                raise UseCaseNotFoundError(f"Unknown use_case_id={use_case_id}")
            if not include_archived and bool(row["archived"]):
                raise UseCaseNotFoundError(f"Unknown use_case_id={use_case_id}")

            version_rows = self._load_use_case_version_rows(conn, use_case_id)
            published_row = _active_published_row(version_rows)
            draft_row = _editable_draft_row(version_rows, published_row)

            draft_definition: UseCaseDefinitionDraft | None = None
            if draft_row is not None:
                draft_definition = self._load_use_case_draft_definition(
                    draft_row["definition_json"]
                )

            published_definition: UseCaseDefinitionPublished | None = None
            if published_row is not None:
                published_definition = self._load_use_case_published_definition(
                    published_row["definition_json"],
                    published_row["version_number"],
                )

            category_id = row["category_id"]
            category_version_number = row["category_version_number"]

            return UseCaseDetail(
                use_case_id=row["id"],
                slug=row["slug"],
                display_name=row["display_name"],
                category_id=category_id,
                category_version_number=category_version_number,
                is_system_default=bool(row["is_system_default"]),
                is_detached=category_id is None or category_version_number is None,
                draft_version_number=draft_row["version_number"] if draft_row else None,
                published_version_number=(
                    published_row["version_number"] if published_row else None
                ),
                draft_definition=draft_definition,
                published_definition=published_definition,
                archived=bool(row["archived"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def create_use_case_with_draft(
        self,
        slug: str,
        category_id: str,
        category_version_number: int,
        draft_definition: UseCaseDefinitionDraft,
        is_system_default: bool = False,
    ) -> UseCaseDetail:
        now = _utc_now()
        use_case_id = uuid.uuid4().hex
        payload = json.dumps(draft_definition.model_dump(), ensure_ascii=True)

        with connect(self.db_path) as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO use_cases(
                        id, slug, display_name, template_id, category_id, category_version_number,
                        is_system_default, created_at, updated_at, archived
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        use_case_id,
                        slug,
                        draft_definition.display_name,
                        category_id,
                        category_id,
                        category_version_number,
                        int(is_system_default),
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"Slug already exists: {slug}") from exc

            conn.execute(
                """
                INSERT INTO use_case_versions(
                    id, use_case_id, version_number, status, definition_json, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid.uuid4().hex,
                    use_case_id,
                    1,
                    VersionStatus.DRAFT.value,
                    payload,
                    now,
                ),
            )
            conn.commit()

        return self.get_use_case_detail(use_case_id)

    def update_draft(
        self,
        use_case_id: str,
        category_id: str,
        category_version_number: int,
        draft_definition: UseCaseDefinitionDraft,
        is_system_default: bool | None = None,
    ) -> UseCaseDetail:
        now = _utc_now()
        payload = json.dumps(draft_definition.model_dump(), ensure_ascii=True)

        with connect(self.db_path) as conn:
            self._assert_use_case_exists(conn, use_case_id)
            version_rows = self._load_use_case_version_rows(conn, use_case_id)
            published_row = _active_published_row(version_rows)
            draft_row = _editable_draft_row(version_rows, published_row)

            if draft_row is None:
                next_version = _next_version_number(
                    conn, "use_case_versions", "use_case_id", use_case_id
                )
                conn.execute(
                    """
                    INSERT INTO use_case_versions(
                        id, use_case_id, version_number, status, definition_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        uuid.uuid4().hex,
                        use_case_id,
                        next_version,
                        VersionStatus.DRAFT.value,
                        payload,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE use_case_versions
                    SET definition_json = ?
                    WHERE id = ?
                    """,
                    (payload, draft_row["id"]),
                )

            conn.execute(
                """
                UPDATE use_cases
                SET display_name = ?,
                    template_id = ?,
                    category_id = ?,
                    category_version_number = ?,
                    is_system_default = COALESCE(?, is_system_default),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    draft_definition.display_name,
                    category_id,
                    category_id,
                    category_version_number,
                    int(is_system_default) if is_system_default is not None else None,
                    now,
                    use_case_id,
                ),
            )
            conn.commit()

        return self.get_use_case_detail(use_case_id)

    def publish_draft(self, use_case_id: str) -> UseCaseDetail:
        now = _utc_now()

        with connect(self.db_path) as conn:
            self._assert_use_case_exists(conn, use_case_id)
            version_rows = self._load_use_case_version_rows(conn, use_case_id)
            published_row = _active_published_row(version_rows)
            draft_row = _editable_draft_row(version_rows, published_row)

            if draft_row is None:
                raise NoDraftAvailableError(
                    f"No draft available to publish for use_case_id={use_case_id}"
                )

            conn.execute(
                """
                UPDATE use_case_versions
                SET status = ?
                WHERE use_case_id = ? AND status = ?
                """,
                (
                    VersionStatus.DRAFT.value,
                    use_case_id,
                    VersionStatus.PUBLISHED.value,
                ),
            )
            conn.execute(
                """
                UPDATE use_case_versions
                SET status = ?
                WHERE id = ?
                """,
                (VersionStatus.PUBLISHED.value, draft_row["id"]),
            )

            definition = self._load_use_case_draft_definition(draft_row["definition_json"])
            conn.execute(
                """
                UPDATE use_cases
                SET display_name = ?, updated_at = ?
                WHERE id = ?
                """,
                (definition.display_name, now, use_case_id),
            )
            conn.commit()

        return self.get_use_case_detail(use_case_id)

    def archive_use_case(self, use_case_id: str) -> UseCaseDetail:
        now = _utc_now()
        with connect(self.db_path) as conn:
            self._assert_use_case_exists(conn, use_case_id)
            conn.execute(
                """
                UPDATE use_cases
                SET archived = 1, updated_at = ?
                WHERE id = ?
                """,
                (now, use_case_id),
            )
            conn.commit()
        return self.get_use_case_detail(use_case_id, include_archived=True)

    def restore_use_case(self, use_case_id: str) -> UseCaseDetail:
        now = _utc_now()
        with connect(self.db_path) as conn:
            self._assert_use_case_exists(conn, use_case_id)
            conn.execute(
                """
                UPDATE use_cases
                SET archived = 0, updated_at = ?
                WHERE id = ?
                """,
                (now, use_case_id),
            )
            conn.commit()
        return self.get_use_case_detail(use_case_id, include_archived=True)

    def get_default_use_case_for_category(
        self,
        category_id: str,
        include_archived: bool = True,
    ) -> UseCaseDetail | None:
        where_archived = "" if include_archived else "AND archived = 0"
        with connect(self.db_path) as conn:
            row = conn.execute(
                f"""
                SELECT id
                FROM use_cases
                WHERE is_system_default = 1
                  AND (category_id = ? OR template_id = ?)
                  {where_archived}
                ORDER BY archived ASC, updated_at DESC
                LIMIT 1
                """,
                (category_id, category_id),
            ).fetchone()
            if row is None:
                return None

        return self.get_use_case_detail(row["id"], include_archived=True)

    def create_or_update_default_use_case_for_category(
        self,
        category_detail: CategoryDetail,
    ) -> UseCaseDetail:
        category_definition = category_detail.published_definition
        category_version_number = category_detail.published_version_number
        if category_definition is None or category_version_number is None:
            raise ValueError(
                "Cannot sync default use case without a published category definition."
            )

        default_definition = UseCaseDefinitionDraft(
            display_name=category_definition.display_name,
            handoff_description=category_definition.default_handoff_description,
            routing_description=category_definition.default_routing_description,
            required_fields=list(category_definition.default_required_fields),
            steps=[
                UseCaseStep.model_validate(step.model_dump())
                for step in category_definition.default_steps
            ],
        )

        existing = self.get_default_use_case_for_category(
            category_detail.category_id,
            include_archived=True,
        )
        if existing is None:
            base_slug = f"default-{category_detail.slug}-{category_detail.category_id[:8]}"
            slug_candidate = base_slug
            suffix = 1
            while True:
                try:
                    created = self.create_use_case_with_draft(
                        slug=slug_candidate,
                        category_id=category_detail.category_id,
                        category_version_number=category_version_number,
                        draft_definition=default_definition,
                        is_system_default=True,
                    )
                    return self.publish_draft(created.use_case_id)
                except ValueError as exc:
                    if "Slug already exists" not in str(exc):
                        raise
                    slug_candidate = f"{base_slug}-{suffix}"
                    suffix += 1

        existing_published_payload = (
            existing.published_definition.model_dump(exclude={"version_number"})
            if existing.published_definition is not None
            else None
        )
        if (
            not existing.archived
            and existing.is_system_default
            and existing.category_id == category_detail.category_id
            and existing.category_version_number == category_version_number
            and existing_published_payload == default_definition.model_dump()
        ):
            return existing

        if existing.archived:
            self.restore_use_case(existing.use_case_id)

        updated = self.update_draft(
            use_case_id=existing.use_case_id,
            category_id=category_detail.category_id,
            category_version_number=category_version_number,
            draft_definition=default_definition,
            is_system_default=True,
        )
        return self.publish_draft(updated.use_case_id)

    def sync_default_use_cases_for_published_categories(
        self,
        category_repository: CategoryRepository,
    ) -> list[UseCaseDetail]:
        synced: list[UseCaseDetail] = []
        for category in category_repository.list_published_category_details():
            synced.append(self.create_or_update_default_use_case_for_category(category))
        return synced

    def archive_default_use_case_for_category(self, category_id: str) -> UseCaseDetail | None:
        default_use_case = self.get_default_use_case_for_category(
            category_id,
            include_archived=True,
        )
        if default_use_case is None:
            return None
        if default_use_case.archived:
            return default_use_case
        return self.archive_use_case(default_use_case.use_case_id)

    def migrate_category_version(
        self,
        use_case_id: str,
        category_id: str,
        category_version_number: int,
    ) -> UseCaseDetail:
        now = _utc_now()
        with connect(self.db_path) as conn:
            self._assert_use_case_exists(conn, use_case_id)
            conn.execute(
                """
                UPDATE use_cases
                SET template_id = ?,
                    category_id = ?,
                    category_version_number = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    category_id,
                    category_id,
                    category_version_number,
                    now,
                    use_case_id,
                ),
            )
            conn.commit()

        return self.get_use_case_detail(use_case_id)

    def list_published_use_cases(self) -> list[PublishedUseCaseSummary]:
        published_items: list[PublishedUseCaseSummary] = []
        with connect(self.db_path) as conn:
            use_cases = conn.execute(
                """
                SELECT id, slug, display_name, category_id, category_version_number
                FROM use_cases
                WHERE archived = 0
                ORDER BY display_name ASC
                """
            ).fetchall()

            for row in use_cases:
                version_rows = self._load_use_case_version_rows(conn, row["id"])
                published_row = _active_published_row(version_rows)
                if published_row is None:
                    continue

                published_definition = self._load_use_case_published_definition(
                    published_row["definition_json"],
                    published_row["version_number"],
                )
                published_items.append(
                    PublishedUseCaseSummary(
                        use_case_id=row["id"],
                        slug=row["slug"],
                        display_name=row["display_name"],
                        category_id=row["category_id"],
                        category_version_number=row["category_version_number"],
                        version_number=published_row["version_number"],
                        definition=published_definition,
                    )
                )

        return published_items

    def seed_if_empty(
        self,
        seed_definitions: list[SeedUseCase],
        categories_by_slug: dict[str, CategoryDetail],
    ) -> None:
        with connect(self.db_path) as conn:
            count_row = conn.execute("SELECT COUNT(1) AS count FROM use_cases").fetchone()
            assert count_row is not None
            if int(count_row["count"]) > 0:
                return

        for seed in seed_definitions:
            category = categories_by_slug.get(seed.category_slug)
            if category is None or category.published_version_number is None:
                continue
            detail = self.create_use_case_with_draft(
                slug=seed.slug,
                category_id=category.category_id,
                category_version_number=category.published_version_number,
                draft_definition=seed.definition,
                is_system_default=seed.is_system_default,
            )
            self.publish_draft(detail.use_case_id)

    def _assert_use_case_exists(self, conn: sqlite3.Connection, use_case_id: str) -> None:
        row = conn.execute(
            "SELECT id FROM use_cases WHERE id = ?",
            (use_case_id,),
        ).fetchone()
        if row is None:
            raise UseCaseNotFoundError(f"Unknown use_case_id={use_case_id}")

    def _load_use_case_version_rows(
        self, conn: sqlite3.Connection, use_case_id: str
    ) -> list[sqlite3.Row]:
        return conn.execute(
            """
            SELECT id, version_number, status, definition_json, created_at
            FROM use_case_versions
            WHERE use_case_id = ?
            ORDER BY version_number DESC
            """,
            (use_case_id,),
        ).fetchall()

    def _load_use_case_draft_definition(self, raw_definition: str) -> UseCaseDefinitionDraft:
        payload = json.loads(raw_definition)
        return UseCaseDefinitionDraft.model_validate(payload)

    def _load_use_case_published_definition(
        self,
        raw_definition: str,
        version_number: int,
    ) -> UseCaseDefinitionPublished:
        payload = json.loads(raw_definition)
        payload["version_number"] = int(version_number)
        return UseCaseDefinitionPublished.model_validate(payload)
