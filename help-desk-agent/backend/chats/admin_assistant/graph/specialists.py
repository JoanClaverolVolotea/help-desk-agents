from __future__ import annotations

from typing import Any

import backend.api.deps as deps
from agents import Agent, function_tool
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from backend.api_internal.validation import parse_csv_list, slugify
from backend.chats.shared.state import current_response_language
from backend.chats.user_assistant.service import publish_category_and_sync
from backend.domain.language_policy import translate_backend_text
from backend.domain.models import CategoryDefinitionInput, UseCaseStep
from backend.domain.templates import (
    list_step_catalog,
    to_category_draft_definition,
    validate_category_definition,
)
from backend.storage import CategoryNotFoundError, NoDraftAvailableError


def build_specialists() -> list[Agent[Any]]:
    @function_tool(
        name_override="list_categories",
        description_override="List current categories and status.",
    )
    def list_categories_tool(include_archived: bool = False) -> str:
        language = current_response_language()
        categories = deps.CATEGORY_REPOSITORY.list_categories(include_archived=include_archived)
        if not categories:
            return translate_backend_text("no_categories_available", language)
        lines = []
        for category in categories:
            lines.append(
                translate_backend_text(
                    "category_status_line",
                    language,
                    category_id=category.category_id,
                    display_name=category.display_name,
                    published_version=category.published_version_number,
                    draft_version=category.draft_version_number,
                    archived=category.archived,
                )
            )
        return "\n".join(lines)

    @function_tool(
        name_override="list_step_catalog",
        description_override="Show all safe step IDs that categories can use.",
    )
    def list_step_catalog_tool() -> str:
        language = current_response_language()
        lines: list[str] = []
        for item in list_step_catalog():
            key = f"step_{item.step_id}"
            try:
                description = translate_backend_text(key, language)
            except KeyError:
                description = item.description
            lines.append(f"- {item.step_id}: {description}")
        return "\n".join(lines)

    @function_tool(
        name_override="create_category_draft",
        description_override=(
            "Create a category draft. Pass comma-separated step IDs and required fields."
        ),
    )
    def create_category_draft_tool(
        display_name: str,
        description: str,
        allowed_step_ids_csv: str,
        default_handoff_description: str,
        default_routing_description: str,
        default_required_fields_csv: str = "",
        default_step_ids_csv: str = "",
    ) -> str:
        language = current_response_language()
        allowed_steps = parse_csv_list(allowed_step_ids_csv)
        default_required_fields = parse_csv_list(default_required_fields_csv)
        default_step_ids = parse_csv_list(default_step_ids_csv) or allowed_steps[:1]

        definition = {
            "display_name": display_name,
            "description": description,
            "allowed_step_ids": allowed_steps,
            "default_handoff_description": default_handoff_description,
            "default_routing_description": default_routing_description,
            "default_required_fields": default_required_fields,
            "default_steps": [
                UseCaseStep(step_id=step_id, params={}).model_dump() for step_id in default_step_ids
            ],
        }

        definition_input = CategoryDefinitionInput.model_validate(definition)
        errors = validate_category_definition(definition_input)
        if errors:
            return translate_backend_text(
                "validation_errors_prefix",
                language,
                errors="; ".join(errors),
            )
        definition_model = to_category_draft_definition(definition_input)

        category_slug = slugify(display_name)
        try:
            detail = deps.CATEGORY_REPOSITORY.create_category_with_draft(
                category_slug, definition_model
            )
        except ValueError as exc:
            return str(exc)

        return translate_backend_text(
            "category_draft_created",
            language,
            category_id=detail.category_id,
            slug=detail.slug,
            draft_version=detail.draft_version_number,
        )

    @function_tool(
        name_override="publish_category_draft",
        description_override="Publish an existing category draft by category_id.",
    )
    async def publish_category_draft_tool(category_id: str) -> str:
        language = current_response_language()
        try:
            detail = await publish_category_and_sync(category_id)
        except (CategoryNotFoundError, NoDraftAvailableError) as exc:
            return str(exc)
        return translate_backend_text(
            "category_published",
            language,
            category_id=detail.category_id,
            version=detail.published_version_number,
        )

    creator_agent = Agent(
        name="Category Creator Specialist",
        handoff_description="Helps tech team create and publish new categories.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You help the technical team create category drafts.

Workflow:
1. Clarify the intended use of the category.
2. Call list_step_catalog and propose safe steps.
3. Call create_category_draft when enough info is available.
4. Ask whether to publish; call publish_category_draft only with explicit confirmation.
5. Reply only in the language of the user's latest message.
6. Do not include translations or bilingual sections.
""",
        tools=[
            list_categories_tool,
            list_step_catalog_tool,
            create_category_draft_tool,
            publish_category_draft_tool,
        ],
    )

    lifecycle_agent = Agent(
        name="Category Lifecycle Specialist",
        handoff_description="Helps with category updates, archive, and restore guidance.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You help the technical team inspect and maintain category lifecycle.

Always start by calling list_categories and then explain what to do next.
If the user asks to create a new category, handoff to Category Creator Specialist.
Reply only in the language of the user's latest message.
Do not include translations or bilingual sections.
""",
        tools=[list_categories_tool],
    )

    return [creator_agent, lifecycle_agent]
