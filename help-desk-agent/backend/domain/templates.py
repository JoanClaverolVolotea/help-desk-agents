from __future__ import annotations

from dataclasses import dataclass

from backend.domain.models import (
    CategoryDefinitionDraft,
    CategoryDefinitionInput,
    StepCatalogItem,
    UseCaseDefinitionDraft,
    UseCaseDefinitionInput,
    UseCaseStep,
)

STEP_CATALOG: dict[str, str] = {
    "verify_requester": "Verify requester identity before account changes.",
    "reset_ecrew_access": "Reset eCrew access and unlock account.",
    "provision_email": "Provision company email account.",
    "provision_efos": "Provision EFOS platform access.",
    "provision_pelesys": "Provision PELESYS learning profile.",
    "append_resolution_note": "Append a closure note to the ticket.",
    "manual_instruction": "Write a deterministic operator-facing instruction.",
}


@dataclass(frozen=True)
class SeedUseCase:
    slug: str
    category_slug: str
    definition: UseCaseDefinitionDraft
    is_system_default: bool = False


def list_step_catalog() -> list[StepCatalogItem]:
    return [
        StepCatalogItem(step_id=step_id, description=description)
        for step_id, description in STEP_CATALOG.items()
    ]


def validate_category_definition(definition: CategoryDefinitionInput) -> list[str]:
    errors: list[str] = []

    if not definition.allowed_step_ids:
        errors.append("At least one allowed step is required.")

    invalid_allowed_steps = [
        step_id for step_id in definition.allowed_step_ids if step_id not in STEP_CATALOG
    ]
    if invalid_allowed_steps:
        errors.append(
            "Allowed steps contain unknown step IDs: "
            + ", ".join(sorted(set(invalid_allowed_steps)))
        )

    default_step_ids = [step.step_id for step in definition.default_steps]
    invalid_default_steps = [step_id for step_id in default_step_ids if step_id not in STEP_CATALOG]
    if invalid_default_steps:
        errors.append(
            "Default steps contain unknown step IDs: "
            + ", ".join(sorted(set(invalid_default_steps)))
        )

    out_of_template_defaults = [
        step_id for step_id in default_step_ids if step_id not in set(definition.allowed_step_ids)
    ]
    if out_of_template_defaults:
        errors.append(
            "Default steps must be included in allowed steps: "
            + ", ".join(sorted(set(out_of_template_defaults)))
        )

    errors.extend(
        _validate_free_form_fields(definition.default_required_fields, "Default required")
    )

    return errors


def validate_use_case_definition(
    definition: UseCaseDefinitionInput,
    allowed_step_ids: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []

    if not definition.steps:
        errors.append("At least one step is required.")

    invalid_step_ids = [
        step.step_id for step in definition.steps if step.step_id not in STEP_CATALOG
    ]
    if invalid_step_ids:
        errors.append("Steps contain unknown step IDs: " + ", ".join(sorted(set(invalid_step_ids))))

    if allowed_step_ids is not None:
        disallowed = [
            step.step_id for step in definition.steps if step.step_id not in allowed_step_ids
        ]
        if disallowed:
            errors.append(
                "Steps are not allowed by the selected category: "
                + ", ".join(sorted(set(disallowed)))
            )

    errors.extend(_validate_free_form_fields(definition.required_fields, "Required"))

    return errors


def to_category_draft_definition(definition: CategoryDefinitionInput) -> CategoryDefinitionDraft:
    return CategoryDefinitionDraft(**definition.model_dump())


def to_use_case_draft_definition(definition: UseCaseDefinitionInput) -> UseCaseDefinitionDraft:
    return UseCaseDefinitionDraft(**definition.model_dump())


def seed_category_definitions() -> list[tuple[str, CategoryDefinitionDraft]]:
    return [
        (
            "access-reset",
            CategoryDefinitionDraft(
                display_name="Reset de acceso / Access reset",
                description=(
                    "Case-aligned access recovery for eCrew login failures, locked accounts, "
                    "and credential reset workflows."
                ),
                allowed_step_ids=[
                    "verify_requester",
                    "reset_ecrew_access",
                    "append_resolution_note",
                    "manual_instruction",
                ],
                default_handoff_description=(
                    "Handles eCrew account recovery requests similar to case USDV-176285."
                ),
                default_routing_description=(
                    "Use this category when a requester cannot access eCrew and needs "
                    "identity verification plus access reset (pattern from USDV-176285)."
                ),
                default_required_fields=[
                    "ticket_id",
                    "requester_name",
                    "requester_id",
                    "affected_platforms",
                ],
                default_steps=[
                    UseCaseStep(step_id="verify_requester", params={}),
                    UseCaseStep(step_id="reset_ecrew_access", params={}),
                    UseCaseStep(
                        step_id="append_resolution_note",
                        params={"note": "Access reset completed and user informed."},
                    ),
                ],
            ),
        ),
        (
            "employee-onboarding",
            CategoryDefinitionDraft(
                display_name="Alta empleado / Employee onboarding",
                description=(
                    "Case-aligned onboarding setup for provisioning E-MAIL, EFOS, and "
                    "PELESYS access for new employees."
                ),
                allowed_step_ids=[
                    "provision_email",
                    "provision_efos",
                    "provision_pelesys",
                    "append_resolution_note",
                    "manual_instruction",
                ],
                default_handoff_description=(
                    "Handles onboarding requests similar to case USDV-176893."
                ),
                default_routing_description=(
                    "Use this category for onboarding tickets that request E-MAIL/EFOS/"
                    "PELESYS account provisioning (pattern from USDV-176893)."
                ),
                default_required_fields=[
                    "ticket_id",
                    "requester_name",
                    "employee_name",
                    "employee_batch",
                    "target_systems",
                ],
                default_steps=[
                    UseCaseStep(step_id="provision_email", params={}),
                    UseCaseStep(step_id="provision_efos", params={}),
                    UseCaseStep(step_id="provision_pelesys", params={}),
                    UseCaseStep(
                        step_id="append_resolution_note",
                        params={"note": "Onboarding setup completed for all requested systems."},
                    ),
                ],
            ),
        ),
    ]


def seed_use_case_definitions() -> list[SeedUseCase]:
    return [
        SeedUseCase(
            slug="reset-acceso-ecrew",
            category_slug="access-reset",
            definition=UseCaseDefinitionDraft(
                display_name="Reset de acceso eCrew",
                handoff_description=(
                    "Handles eCrew login and account recovery requests based on case USDV-176285."
                ),
                routing_description=(
                    "Ticket example: USDV-176285. Use when a requester cannot log in to "
                    "eCrew and needs verification plus access restoration."
                ),
                required_fields=[
                    "ticket_id",
                    "requester_name",
                    "requester_id",
                    "affected_platforms",
                ],
                steps=[
                    UseCaseStep(step_id="verify_requester", params={}),
                    UseCaseStep(step_id="reset_ecrew_access", params={}),
                    UseCaseStep(
                        step_id="append_resolution_note",
                        params={"note": "eCrew access reset complete."},
                    ),
                ],
            ),
        ),
        SeedUseCase(
            slug="alta-email-efos-pelesys",
            category_slug="employee-onboarding",
            definition=UseCaseDefinitionDraft(
                display_name="Alta E-MAIL/EFOS/PELESYS",
                handoff_description=(
                    "Handles onboarding setup for E-MAIL, EFOS, and PELESYS based on case "
                    "USDV-176893."
                ),
                routing_description=(
                    "Ticket example: USDV-176893. Use for onboarding requests that include "
                    "employee identity plus target systems (E-MAIL, EFOS, PELESYS)."
                ),
                required_fields=[
                    "ticket_id",
                    "requester_name",
                    "employee_name",
                    "employee_batch",
                    "target_systems",
                ],
                steps=[
                    UseCaseStep(step_id="provision_email", params={}),
                    UseCaseStep(step_id="provision_efos", params={}),
                    UseCaseStep(step_id="provision_pelesys", params={}),
                    UseCaseStep(
                        step_id="append_resolution_note",
                        params={"note": "Onboarding setup complete."},
                    ),
                ],
            ),
        ),
    ]


def _validate_free_form_fields(values: list[str], prefix: str) -> list[str]:
    errors: list[str] = []
    normalized: list[str] = []

    for raw_value in values:
        value = raw_value.strip()
        if not value:
            errors.append(f"{prefix} fields cannot contain empty values.")
            continue
        normalized.append(value)

    if len(set(normalized)) != len(normalized):
        errors.append(f"{prefix} fields must be unique.")

    return errors
