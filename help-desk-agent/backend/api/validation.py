from __future__ import annotations

import re
import uuid

from backend.domain.models import UseCaseDefinitionInput
from backend.domain.templates import validate_use_case_definition
from backend.storage import CategoryNotFoundError, CategoryRepository


def slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")
    return normalized or uuid.uuid4().hex[:12]


def parse_csv_list(raw_value: str) -> list[str]:
    return [token.strip() for token in raw_value.split(",") if token.strip()]


def validate_use_case_payload(
    category_repository: CategoryRepository,
    category_id: str,
    definition_input: UseCaseDefinitionInput,
) -> tuple[list[str], int]:
    category_definition = category_repository.get_published_category_definition(category_id)
    validation_errors = validate_use_case_definition(
        definition_input,
        allowed_step_ids=set(category_definition.allowed_step_ids),
    )
    return validation_errors, category_definition.version_number


__all__ = ["slugify", "parse_csv_list", "validate_use_case_payload", "CategoryNotFoundError"]
