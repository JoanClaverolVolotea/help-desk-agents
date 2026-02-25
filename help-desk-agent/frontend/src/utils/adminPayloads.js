export const STEP_LABELS = {
  verify_requester: "Verificar solicitante / Verify requester",
  reset_ecrew_access: "Reset eCrew access",
  provision_email: "Provision E-MAIL",
  provision_efos: "Provision EFOS",
  provision_pelesys: "Provision PELESYS",
  append_resolution_note: "Append resolution note",
  manual_instruction: "Manual instruction",
};

export function parseCsv(rawValue) {
  return rawValue
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function joinCsv(values) {
  return values.join(", ");
}

export function defaultCategoryWizard(stepCatalog) {
  const stepIds = stepCatalog.map((item) => item.step_id);
  const defaultStep = stepIds[0] ?? "manual_instruction";

  return {
    categoryId: null,
    slug: "",
    displayName: "",
    description: "",
    allowedStepIds: stepIds.slice(0, Math.min(3, stepIds.length)),
    defaultHandoffDescription: "",
    defaultRoutingDescription: "",
    defaultRequiredFieldsText: "ticket_id",
    defaultStepIds: [defaultStep],
  };
}

export function categoryWizardFromDetail(detail) {
  const definition = detail.draft_definition ?? detail.published_definition;
  if (!definition) {
    return null;
  }

  return {
    categoryId: detail.category_id,
    slug: detail.slug,
    displayName: definition.display_name,
    description: definition.description,
    allowedStepIds: [...definition.allowed_step_ids],
    defaultHandoffDescription: definition.default_handoff_description,
    defaultRoutingDescription: definition.default_routing_description,
    defaultRequiredFieldsText: joinCsv(definition.default_required_fields),
    defaultStepIds: definition.default_steps.map((step) => step.step_id),
  };
}

export function defaultUseCaseWizard(categoryId, allowedStepIds) {
  const fallbackStep = allowedStepIds[0] ?? "manual_instruction";

  return {
    useCaseId: null,
    slug: "",
    categoryId,
    displayName: "",
    handoffDescription: "",
    routingDescription: "",
    requiredFieldsText: "ticket_id",
    steps: [{ step_id: fallbackStep, params: {} }],
  };
}

export function useCaseWizardFromDetail(detail) {
  const definition = detail.draft_definition ?? detail.published_definition;
  if (!definition) {
    return null;
  }

  return {
    useCaseId: detail.use_case_id,
    slug: detail.slug,
    categoryId: detail.category_id ?? "",
    displayName: definition.display_name,
    handoffDescription: definition.handoff_description,
    routingDescription: definition.routing_description,
    requiredFieldsText: joinCsv(definition.required_fields),
    steps: definition.steps.map((step) => ({
      step_id: step.step_id,
      params: { ...step.params },
    })),
  };
}

export function buildCategoryPayload(wizardState) {
  return {
    slug: wizardState.slug || undefined,
    definition: {
      display_name: wizardState.displayName,
      description: wizardState.description,
      allowed_step_ids: wizardState.allowedStepIds,
      default_handoff_description: wizardState.defaultHandoffDescription,
      default_routing_description: wizardState.defaultRoutingDescription,
      default_required_fields: parseCsv(wizardState.defaultRequiredFieldsText),
      default_steps: wizardState.defaultStepIds.map((stepId) => ({ step_id: stepId, params: {} })),
    },
  };
}

export function buildUseCasePayload(wizardState) {
  return {
    slug: wizardState.slug || undefined,
    category_id: wizardState.categoryId,
    definition: {
      display_name: wizardState.displayName,
      handoff_description: wizardState.handoffDescription,
      routing_description: wizardState.routingDescription,
      required_fields: parseCsv(wizardState.requiredFieldsText),
      steps: wizardState.steps,
    },
  };
}

export function parseValidationError(errorMessage) {
  try {
    const parsed = JSON.parse(errorMessage);
    if (parsed.detail && parsed.detail.validation_errors) {
      return parsed.detail.validation_errors.join(" ");
    }
  } catch {
    return errorMessage;
  }
  return errorMessage;
}
