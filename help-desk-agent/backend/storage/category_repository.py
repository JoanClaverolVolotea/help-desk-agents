from __future__ import annotations

import json
import pathlib
import sqlite3
import uuid
from typing import cast

from backend.domain.models import (
    CategoryDefinitionDraft,
    CategoryDefinitionPublished,
    CategoryDetail,
    CategoryListItem,
    VersionStatus,
)

from .db import connect, init_schema, resolve_db_path
from .errors import CategoryNotFoundError, NoDraftAvailableError
from .sql_helpers import _active_published_row, _editable_draft_row, _next_version_number, _utc_now


class CategoryRepository:
    def __init__(self, db_path: str | pathlib.Path | None = None) -> None:
        if isinstance(db_path, pathlib.Path):
            self.db_path = db_path
        else:
            self.db_path = resolve_db_path(db_path)

    def initialize(self) -> None:
        with connect(self.db_path) as conn:
            init_schema(conn)

    def list_categories(self, include_archived: bool = False) -> list[CategoryListItem]:
        where_clause = "" if include_archived else "WHERE archived = 0"
        query = f"""
            SELECT id, slug, display_name, created_at, updated_at, archived
            FROM categories
            {where_clause}
            ORDER BY updated_at DESC
        """

        with connect(self.db_path) as conn:
            rows = conn.execute(query).fetchall()
            items: list[CategoryListItem] = []
            for row in rows:
                version_rows = self._load_category_version_rows(conn, row["id"])
                published_row = _active_published_row(version_rows)
                draft_row = _editable_draft_row(version_rows, published_row)
                items.append(
                    CategoryListItem(
                        category_id=row["id"],
                        slug=row["slug"],
                        display_name=row["display_name"],
                        draft_version_number=draft_row["version_number"] if draft_row else None,
                        published_version_number=(
                            published_row["version_number"] if published_row else None
                        ),
                        archived=bool(row["archived"]),
                        updated_at=row["updated_at"],
                    )
                )
            return items

    def get_category_detail(
        self, category_id: str, include_archived: bool = True
    ) -> CategoryDetail:
        with connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, slug, display_name, created_at, updated_at, archived
                FROM categories
                WHERE id = ?
                """,
                (category_id,),
            ).fetchone()

            if row is None:
                raise CategoryNotFoundError(f"Unknown category_id={category_id}")
            if not include_archived and bool(row["archived"]):
                raise CategoryNotFoundError(f"Unknown category_id={category_id}")

            version_rows = self._load_category_version_rows(conn, category_id)
            published_row = _active_published_row(version_rows)
            draft_row = _editable_draft_row(version_rows, published_row)

            draft_definition: CategoryDefinitionDraft | None = None
            if draft_row is not None:
                draft_definition = self._load_category_draft_definition(
                    draft_row["definition_json"]
                )

            published_definition: CategoryDefinitionPublished | None = None
            if published_row is not None:
                published_definition = self._load_category_published_definition(
                    published_row["definition_json"],
                    published_row["version_number"],
                )

            return CategoryDetail(
                category_id=row["id"],
                slug=row["slug"],
                display_name=row["display_name"],
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

    def create_category_with_draft(
        self,
        slug: str,
        draft_definition: CategoryDefinitionDraft,
    ) -> CategoryDetail:
        now = _utc_now()
        category_id = uuid.uuid4().hex
        payload = json.dumps(draft_definition.model_dump(), ensure_ascii=True)

        with connect(self.db_path) as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO categories(
                        id, slug, display_name, created_at, updated_at, archived
                    )
                    VALUES(?, ?, ?, ?, ?, 0)
                    """,
                    (category_id, slug, draft_definition.display_name, now, now),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"Slug already exists: {slug}") from exc

            conn.execute(
                """
                INSERT INTO category_versions(
                    id, category_id, version_number, status, definition_json, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid.uuid4().hex,
                    category_id,
                    1,
                    VersionStatus.DRAFT.value,
                    payload,
                    now,
                ),
            )
            conn.commit()

        return self.get_category_detail(category_id)

    def update_draft(
        self,
        category_id: str,
        draft_definition: CategoryDefinitionDraft,
    ) -> CategoryDetail:
        now = _utc_now()
        payload = json.dumps(draft_definition.model_dump(), ensure_ascii=True)

        with connect(self.db_path) as conn:
            row = self._assert_category_exists(conn, category_id)
            version_rows = self._load_category_version_rows(conn, category_id)
            published_row = _active_published_row(version_rows)
            draft_row = _editable_draft_row(version_rows, published_row)

            if draft_row is None:
                next_version = _next_version_number(
                    conn, "category_versions", "category_id", category_id
                )
                conn.execute(
                    """
                    INSERT INTO category_versions(
                        id, category_id, version_number, status, definition_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        uuid.uuid4().hex,
                        category_id,
                        next_version,
                        VersionStatus.DRAFT.value,
                        payload,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE category_versions
                    SET definition_json = ?
                    WHERE id = ?
                    """,
                    (payload, draft_row["id"]),
                )

            conn.execute(
                """
                UPDATE categories
                SET display_name = ?, updated_at = ?
                WHERE id = ?
                """,
                (draft_definition.display_name, now, row["id"]),
            )
            conn.commit()

        return self.get_category_detail(category_id)

    def publish_draft(self, category_id: str) -> CategoryDetail:
        now = _utc_now()

        with connect(self.db_path) as conn:
            self._assert_category_exists(conn, category_id)
            version_rows = self._load_category_version_rows(conn, category_id)
            published_row = _active_published_row(version_rows)
            draft_row = _editable_draft_row(version_rows, published_row)

            if draft_row is None:
                raise NoDraftAvailableError(
                    f"No draft available to publish for category_id={category_id}"
                )

            conn.execute(
                """
                UPDATE category_versions
                SET status = ?
                WHERE category_id = ? AND status = ?
                """,
                (
                    VersionStatus.DRAFT.value,
                    category_id,
                    VersionStatus.PUBLISHED.value,
                ),
            )
            conn.execute(
                """
                UPDATE category_versions
                SET status = ?
                WHERE id = ?
                """,
                (VersionStatus.PUBLISHED.value, draft_row["id"]),
            )

            definition = self._load_category_draft_definition(draft_row["definition_json"])
            conn.execute(
                """
                UPDATE categories
                SET display_name = ?, updated_at = ?
                WHERE id = ?
                """,
                (definition.display_name, now, category_id),
            )
            conn.commit()

        return self.get_category_detail(category_id)

    def archive_category(self, category_id: str) -> CategoryDetail:
        now = _utc_now()

        with connect(self.db_path) as conn:
            self._assert_category_exists(conn, category_id)
            conn.execute(
                """
                UPDATE categories
                SET archived = 1, updated_at = ?
                WHERE id = ?
                """,
                (now, category_id),
            )
            conn.execute(
                """
                UPDATE use_cases
                SET category_id = NULL,
                    category_version_number = NULL,
                    updated_at = ?
                WHERE category_id = ?
                  AND (is_system_default = 0 OR is_system_default IS NULL)
                """,
                (now, category_id),
            )
            conn.commit()

        return self.get_category_detail(category_id, include_archived=True)

    def restore_category(self, category_id: str) -> CategoryDetail:
        now = _utc_now()
        with connect(self.db_path) as conn:
            self._assert_category_exists(conn, category_id)
            conn.execute(
                """
                UPDATE categories
                SET archived = 0, updated_at = ?
                WHERE id = ?
                """,
                (now, category_id),
            )
            conn.commit()
        return self.get_category_detail(category_id, include_archived=True)

    def get_published_category_definition(
        self,
        category_id: str,
        version_number: int | None = None,
    ) -> CategoryDefinitionPublished:
        with connect(self.db_path) as conn:
            category_row = conn.execute(
                """
                SELECT id, archived
                FROM categories
                WHERE id = ?
                """,
                (category_id,),
            ).fetchone()
            if category_row is None:
                raise CategoryNotFoundError(f"Unknown category_id={category_id}")
            if bool(category_row["archived"]):
                raise CategoryNotFoundError(f"Archived category_id={category_id}")

            if version_number is None:
                version_row = conn.execute(
                    """
                    SELECT definition_json, version_number
                    FROM category_versions
                    WHERE category_id = ? AND status = ?
                    ORDER BY version_number DESC
                    LIMIT 1
                    """,
                    (category_id, VersionStatus.PUBLISHED.value),
                ).fetchone()
            else:
                version_row = conn.execute(
                    """
                    SELECT definition_json, version_number
                    FROM category_versions
                    WHERE category_id = ? AND status = ? AND version_number = ?
                    """,
                    (category_id, VersionStatus.PUBLISHED.value, version_number),
                ).fetchone()

            if version_row is None:
                raise CategoryNotFoundError(
                    f"No published version available for category_id={category_id}"
                )

            return self._load_category_published_definition(
                version_row["definition_json"],
                version_row["version_number"],
            )

    def list_published_category_details(self) -> list[CategoryDetail]:
        items = self.list_categories(include_archived=False)
        published: list[CategoryDetail] = []
        for item in items:
            detail = self.get_category_detail(item.category_id, include_archived=False)
            if detail.published_definition is None:
                continue
            published.append(detail)
        return published

    def seed_if_empty(
        self,
        seed_definitions: list[tuple[str, CategoryDefinitionDraft]],
    ) -> dict[str, CategoryDetail]:
        with connect(self.db_path) as conn:
            count_row = conn.execute("SELECT COUNT(1) AS count FROM categories").fetchone()
            assert count_row is not None
            if int(count_row["count"]) > 0:
                return self._categories_by_slug(conn)

        for slug, definition in seed_definitions:
            detail = self.create_category_with_draft(slug=slug, draft_definition=definition)
            self.publish_draft(detail.category_id)

        with connect(self.db_path) as conn:
            return self._categories_by_slug(conn)

    def _assert_category_exists(self, conn: sqlite3.Connection, category_id: str) -> sqlite3.Row:
        row = conn.execute(
            "SELECT id FROM categories WHERE id = ?",
            (category_id,),
        ).fetchone()
        if row is None:
            raise CategoryNotFoundError(f"Unknown category_id={category_id}")
        return cast(sqlite3.Row, row)

    def _categories_by_slug(self, conn: sqlite3.Connection) -> dict[str, CategoryDetail]:
        rows = conn.execute(
            """
            SELECT id, slug
            FROM categories
            WHERE archived = 0
            """
        ).fetchall()
        result: dict[str, CategoryDetail] = {}
        for row in rows:
            detail = self.get_category_detail(row["id"], include_archived=False)
            result[row["slug"]] = detail
        return result

    def _load_category_version_rows(
        self,
        conn: sqlite3.Connection,
        category_id: str,
    ) -> list[sqlite3.Row]:
        return conn.execute(
            """
            SELECT id, version_number, status, definition_json, created_at
            FROM category_versions
            WHERE category_id = ?
            ORDER BY version_number DESC
            """,
            (category_id,),
        ).fetchall()

    def _load_category_draft_definition(self, raw_definition: str) -> CategoryDefinitionDraft:
        payload = json.loads(raw_definition)
        return CategoryDefinitionDraft.model_validate(payload)

    def _load_category_published_definition(
        self,
        raw_definition: str,
        version_number: int,
    ) -> CategoryDefinitionPublished:
        payload = json.loads(raw_definition)
        payload["version_number"] = int(version_number)
        return CategoryDefinitionPublished.model_validate(payload)
