import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import AdminTable from "../components/AdminTable";
import Breadcrumb from "../components/Breadcrumb";
import WizardModal from "../components/WizardModal";
import { useI18n } from "../i18n/useI18n";
import {
  archiveUseCase,
  createUseCase,
  getCategory,
  getUseCase,
  listCategories,
  listTickets,
  listUseCases,
  publishUseCase,
  readableError,
  restoreUseCase,
  updateUseCaseDraft,
} from "../api";
import {
  type UseCaseWizardState,
  type UseCaseWizardStep,
  STEP_LABELS,
  buildUseCasePayload,
  defaultUseCaseWizard,
  parseValidationError,
  useCaseWizardFromDetail,
} from "../utils/adminPayloads";
import type {
  CategoryDetail,
  CategorySummary,
  TicketSummary,
  UseCaseDetail,
  UseCaseSummary,
} from "../types";

type UseCaseRow = UseCaseSummary & { id: string };

export default function ITAdminUseCasesPage(): JSX.Element {
  const { t } = useI18n();
  const [searchParams] = useSearchParams();
  const filterCategoryId = searchParams.get("category_id") || "";

  const [categories, setCategories] = useState<CategorySummary[]>([]);
  const [useCases, setUseCases] = useState<UseCaseSummary[]>([]);
  const [ticketCounts, setTicketCounts] = useState<Record<string, number>>({});
  const [categoryDetailsById, setCategoryDetailsById] = useState<Record<string, CategoryDetail>>({});
  const [includeArchivedUseCases, setIncludeArchivedUseCases] = useState(false);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminError, setAdminError] = useState("");

  const [showUseCaseWizard, setShowUseCaseWizard] = useState(false);
  const [useCaseWizardMode, setUseCaseWizardMode] = useState<"create" | "edit">("create");
  const [useCaseWizardStep, setUseCaseWizardStep] = useState(1);
  const [useCaseWizardBusy, setUseCaseWizardBusy] = useState(false);
  const [useCaseWizardError, setUseCaseWizardError] = useState("");
  const [useCaseWizardState, setUseCaseWizardState] = useState<UseCaseWizardState | null>(null);

  const loadAdminData = async (): Promise<void> => {
    setAdminLoading(true);
    setAdminError("");

    try {
      const [categoriesResponse, useCasesResponse, ticketsResponse] = await Promise.all([
        listCategories(true),
        listUseCases(includeArchivedUseCases),
        listTickets({ limit: 200, offset: 0 }),
      ]);
      setCategories(categoriesResponse.items);
      setUseCases(useCasesResponse.items);

      const counts: Record<string, number> = {};
      for (const ticket of ticketsResponse.items as TicketSummary[]) {
        if (ticket.use_case_id) {
          counts[ticket.use_case_id] = (counts[ticket.use_case_id] || 0) + 1;
        }
      }
      setTicketCounts(counts);
    } catch (error) {
      setAdminError(readableError(error));
    } finally {
      setAdminLoading(false);
    }
  };

  useEffect(() => {
    void loadAdminData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [includeArchivedUseCases]);

  const ensureCategoryDetail = async (categoryId: string): Promise<CategoryDetail | null> => {
    if (!categoryId) {
      return null;
    }

    if (categoryDetailsById[categoryId]) {
      return categoryDetailsById[categoryId];
    }

    const response = await getCategory(categoryId);
    setCategoryDetailsById((prev) => ({ ...prev, [categoryId]: response.category }));
    return response.category;
  };

  const openCreateUseCaseWizard = async (): Promise<void> => {
    const availableCategories = categories.filter(
      (category) => !category.archived && category.published_version_number !== null,
    );

    if (availableCategories.length === 0) {
      setAdminError(t("useCasesPage.noPublishedCategories"));
      return;
    }

    const categoryId = availableCategories[0].category_id;
    const detail = await ensureCategoryDetail(categoryId);
    const allowedStepIds = detail?.published_definition?.allowed_step_ids ?? [];

    setUseCaseWizardMode("create");
    setUseCaseWizardStep(1);
    setUseCaseWizardError("");
    setUseCaseWizardState(defaultUseCaseWizard(categoryId, allowedStepIds));
    setShowUseCaseWizard(true);
  };

  const openEditUseCaseWizard = async (useCaseId: string): Promise<void> => {
    setUseCaseWizardBusy(true);
    setUseCaseWizardError("");

    try {
      const response = await getUseCase(useCaseId);
      const wizard = useCaseWizardFromDetail(response.use_case);
      if (!wizard) {
        throw new Error(t("useCasesPage.noDefinition"));
      }

      if (wizard.categoryId) {
        await ensureCategoryDetail(wizard.categoryId);
      }

      setUseCaseWizardMode("edit");
      setUseCaseWizardStep(1);
      setUseCaseWizardState(wizard);
      setShowUseCaseWizard(true);
    } catch (error) {
      setUseCaseWizardError(readableError(error));
    } finally {
      setUseCaseWizardBusy(false);
    }
  };

  const closeUseCaseWizard = (): void => {
    setShowUseCaseWizard(false);
    setUseCaseWizardState(null);
    setUseCaseWizardStep(1);
    setUseCaseWizardError("");
  };

  const setUseCaseField = <K extends keyof UseCaseWizardState>(
    key: K,
    value: UseCaseWizardState[K],
  ): void => {
    setUseCaseWizardState((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  const selectedUseCaseCategory = useCaseWizardState?.categoryId
    ? categoryDetailsById[useCaseWizardState.categoryId]
    : null;
  const selectedUseCaseAllowedSteps =
    selectedUseCaseCategory?.published_definition?.allowed_step_ids ?? [];

  const onUseCaseCategoryChange = async (categoryId: string): Promise<void> => {
    setUseCaseField("categoryId", categoryId);

    const detail = await ensureCategoryDetail(categoryId);
    const allowedStepIds = detail?.published_definition?.allowed_step_ids ?? [];

    setUseCaseWizardState((prev) => {
      if (!prev) {
        return prev;
      }

      const sanitizedSteps = prev.steps
        .filter((step) => allowedStepIds.includes(step.step_id))
        .map((step) => ({ ...step, params: { ...step.params } }));

      if (sanitizedSteps.length > 0) {
        return { ...prev, categoryId, steps: sanitizedSteps };
      }

      const fallbackStep = allowedStepIds[0] ?? "manual_instruction";
      return {
        ...prev,
        categoryId,
        steps: [{ step_id: fallbackStep, params: {} }],
      };
    });
  };

  const updateUseCaseStepAt = (
    index: number,
    updater: (step: UseCaseWizardStep) => UseCaseWizardStep,
  ): void => {
    setUseCaseWizardState((prev) => {
      if (!prev) {
        return prev;
      }
      const nextSteps = [...prev.steps];
      nextSteps[index] = updater(nextSteps[index]);
      return { ...prev, steps: nextSteps };
    });
  };

  const addUseCaseStep = (): void => {
    const fallbackStep = selectedUseCaseAllowedSteps[0] ?? "manual_instruction";
    setUseCaseWizardState((prev) =>
      prev
        ? {
            ...prev,
            steps: [...prev.steps, { step_id: fallbackStep, params: {} }],
          }
        : prev,
    );
  };

  const removeUseCaseStep = (index: number): void => {
    setUseCaseWizardState((prev) =>
      prev
        ? {
            ...prev,
            steps: prev.steps.filter((_, itemIndex) => itemIndex !== index),
          }
        : prev,
    );
  };

  const moveUseCaseStep = (index: number, direction: number): void => {
    setUseCaseWizardState((prev) => {
      if (!prev) {
        return prev;
      }

      const targetIndex = index + direction;
      if (targetIndex < 0 || targetIndex >= prev.steps.length) {
        return prev;
      }

      const nextSteps = [...prev.steps];
      const [removed] = nextSteps.splice(index, 1);
      nextSteps.splice(targetIndex, 0, removed);
      return { ...prev, steps: nextSteps };
    });
  };

  const validateUseCaseWizard = (wizardState: UseCaseWizardState): string => {
    if (!wizardState.categoryId) {
      return t("useCasesPage.validationSelectCategory");
    }
    if (!wizardState.displayName.trim()) {
      return t("useCasesPage.validationDisplayName");
    }
    if (!wizardState.handoffDescription.trim()) {
      return t("useCasesPage.validationHandoff");
    }
    if (!wizardState.routingDescription.trim()) {
      return t("useCasesPage.validationRouting");
    }
    if (wizardState.steps.length === 0) {
      return t("useCasesPage.validationSteps");
    }
    return "";
  };

  const saveUseCaseDraft = async (): Promise<UseCaseDetail | null> => {
    if (!useCaseWizardState) {
      return null;
    }

    const validationError = validateUseCaseWizard(useCaseWizardState);
    if (validationError) {
      setUseCaseWizardError(validationError);
      return null;
    }

    setUseCaseWizardBusy(true);
    setUseCaseWizardError("");

    const payload = buildUseCasePayload(useCaseWizardState);
    try {
      if (useCaseWizardState.useCaseId) {
        const response = await updateUseCaseDraft(useCaseWizardState.useCaseId, {
          category_id: payload.category_id,
          definition: payload.definition,
        });
        await loadAdminData();
        return response.use_case;
      }

      const response = await createUseCase(payload);
      setUseCaseWizardState((prev) =>
        prev ? { ...prev, useCaseId: response.use_case.use_case_id } : prev,
      );
      await loadAdminData();
      return response.use_case;
    } catch (error) {
      setUseCaseWizardError(parseValidationError(readableError(error)));
      return null;
    } finally {
      setUseCaseWizardBusy(false);
    }
  };

  const publishUseCaseFromWizard = async (): Promise<void> => {
    const saved = await saveUseCaseDraft();
    if (!saved) {
      return;
    }

    try {
      await publishUseCase(saved.use_case_id);
      await loadAdminData();
      closeUseCaseWizard();
    } catch (error) {
      setUseCaseWizardError(readableError(error));
    }
  };

  const publishUseCaseFromList = async (useCaseId: string): Promise<void> => {
    setAdminError("");
    try {
      await publishUseCase(useCaseId);
      await loadAdminData();
    } catch (error) {
      setAdminError(readableError(error));
    }
  };

  const archiveUseCaseFromList = async (useCaseId: string): Promise<void> => {
    setAdminError("");
    try {
      await archiveUseCase(useCaseId);
      await loadAdminData();
    } catch (error) {
      setAdminError(readableError(error));
    }
  };

  const restoreUseCaseFromList = async (useCaseId: string): Promise<void> => {
    setAdminError("");
    try {
      await restoreUseCase(useCaseId);
      await loadAdminData();
    } catch (error) {
      setAdminError(readableError(error));
    }
  };

  const filteredUseCases = filterCategoryId
    ? useCases.filter((item) => item.category_id === filterCategoryId)
    : useCases;

  const filterCategoryName = filterCategoryId
    ? categories.find((category) => category.category_id === filterCategoryId)?.display_name
    : null;

  return (
    <section className="tab-panel admin-panel it-console-panel it-console-use-cases">
      <Breadcrumb
        items={[
          { label: t("common.dashboard"), to: "/it/dashboard" },
          ...(filterCategoryName
            ? [{ label: filterCategoryName, to: "/it/admin/categories" }]
            : []),
          { label: t("common.runbooks") },
        ]}
      />
      <div className="admin-toolbar">
        <h2>
          {filterCategoryName
            ? t("useCasesPage.headingWithCategory", { category: filterCategoryName })
            : t("useCasesPage.heading")}
        </h2>
        <div className="admin-toolbar-actions">
          <button type="button" className="ghost" onClick={() => void loadAdminData()} disabled={adminLoading}>
            {t("common.refresh")}
          </button>
          <button type="button" className="primary" onClick={() => void openCreateUseCaseWizard()}>
            {t("useCasesPage.create")}
          </button>
        </div>
      </div>

      <label className="toggle-row">
        <input
          type="checkbox"
          checked={includeArchivedUseCases}
          onChange={(event) => setIncludeArchivedUseCases(event.target.checked)}
        />
        <span>{t("common.showArchived")}</span>
      </label>
      <section className="console-clarity-card">
        <h3>{t("useCasesPage.cardTitle")}</h3>
        <p>{t("useCasesPage.cardBody")}</p>
      </section>

      {adminLoading ? <p className="helper">{t("common.loadingData")}</p> : null}
      {adminError ? <p className="error-text">{adminError}</p> : null}

      <AdminTable<UseCaseRow>
        columns={[
          {
            key: "name",
            label: t("useCasesPage.tableName"),
            render: (row) => (
              <>
                <strong>{row.display_name}</strong>
                {row.is_system_default ? (
                  <span className="badge default" style={{ marginLeft: "0.4rem" }}>
                    {t("common.auto")}
                  </span>
                ) : null}
              </>
            ),
          },
          {
            key: "category",
            label: t("useCasesPage.tableCategory"),
            render: (row) =>
              row.category_id ? (
                <Link to="/it/admin/categories">
                  {categories.find((category) => category.category_id === row.category_id)?.display_name ||
                    row.category_id}
                </Link>
              ) : (
                <span className="badge detached">{t("common.noCategory")}</span>
              ),
          },
          {
            key: "status",
            label: t("useCasesPage.tableStatus"),
            render: (row) => (
              <div className="badge-row">
                <span className={row.archived ? "badge archived" : "badge published"}>
                  {row.archived ? t("common.archived") : t("common.active")}
                </span>
                {row.draft_version_number && !row.is_system_default ? (
                  <span className="badge draft">{t("common.unpublishedChanges")}</span>
                ) : null}
              </div>
            ),
          },
          {
            key: "tickets",
            label: t("useCasesPage.tableTickets"),
            render: (row) => (
              <Link to={`/it/admin/tickets?use_case_id=${row.use_case_id}`}>
                {ticketCounts[row.use_case_id] || 0}
              </Link>
            ),
          },
          {
            key: "actions",
            label: "",
            render: (row) =>
              row.is_system_default ? null : (
                <div className="use-case-actions" style={{ flexDirection: "row" }}>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => void openEditUseCaseWizard(row.use_case_id)}
                  >
                    {t("common.edit")}
                  </button>
                  <button
                    type="button"
                    className="primary"
                    disabled={!row.draft_version_number || row.archived}
                    onClick={() => void publishUseCaseFromList(row.use_case_id)}
                  >
                    {t("common.publish")}
                  </button>
                  {row.archived ? (
                    <button
                      type="button"
                      className="ghost"
                      onClick={() => void restoreUseCaseFromList(row.use_case_id)}
                    >
                      {t("common.restore")}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="ghost"
                      onClick={() => void archiveUseCaseFromList(row.use_case_id)}
                    >
                      {t("common.archive")}
                    </button>
                  )}
                </div>
              ),
          },
        ]}
        rows={filteredUseCases.map((item) => ({ ...item, id: item.use_case_id }))}
        emptyMessage={t("useCasesPage.emptyRunbooks")}
      />

      {showUseCaseWizard && useCaseWizardState ? (
        <WizardModal
          title={useCaseWizardMode === "create" ? t("useCasesPage.wizardNew") : t("useCasesPage.wizardEdit")}
          step={useCaseWizardStep}
          totalSteps={4}
          onClose={closeUseCaseWizard}
          error={useCaseWizardError}
          navActions={
            <>
              <button
                type="button"
                className="ghost"
                onClick={() => setUseCaseWizardStep((prev) => Math.max(1, prev - 1))}
                disabled={useCaseWizardStep === 1}
              >
                {t("common.previous")}
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => setUseCaseWizardStep((prev) => Math.min(4, prev + 1))}
                disabled={useCaseWizardStep === 4}
              >
                {t("common.next")}
              </button>
            </>
          }
          submitActions={
            <>
              <button
                type="button"
                className="ghost"
                onClick={() => void saveUseCaseDraft()}
                disabled={useCaseWizardBusy}
              >
                {t("common.saveDraft")}
              </button>
              <button
                type="button"
                className="primary"
                onClick={() => void publishUseCaseFromWizard()}
                disabled={useCaseWizardBusy}
              >
                {t("common.saveAndPublish")}
              </button>
            </>
          }
        >
          {useCaseWizardStep === 1 ? (
            <div className="form-grid">
              <label>
                {t("useCasesPage.formCategoryPublished")}
                <select
                  value={useCaseWizardState.categoryId}
                  onChange={(event) => void onUseCaseCategoryChange(event.target.value)}
                >
                  <option value="">{t("useCasesPage.formSelectCategory")}</option>
                  {categories
                    .filter(
                      (category) => !category.archived && category.published_version_number !== null,
                    )
                    .map((category) => (
                      <option key={category.category_id} value={category.category_id}>
                        {category.display_name}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                {t("useCasesPage.formDisplayName")}
                <input
                  value={useCaseWizardState.displayName}
                  onChange={(event) => setUseCaseField("displayName", event.target.value)}
                />
              </label>
              <label>
                {t("useCasesPage.formSlug")}
                <span className="helper" style={{ fontSize: "0.78rem", fontWeight: 400 }}>
                  {t("useCasesPage.formSlugHelp")}
                </span>
                <input
                  value={useCaseWizardState.slug}
                  onChange={(event) => setUseCaseField("slug", event.target.value)}
                />
              </label>
            </div>
          ) : null}

          {useCaseWizardStep === 2 ? (
            <div className="form-grid">
              <label>
                {t("useCasesPage.formHandoff")}
                <span className="helper" style={{ fontSize: "0.78rem", fontWeight: 400 }}>
                  {t("useCasesPage.formHandoffHelp")}
                </span>
                <textarea
                  rows={3}
                  value={useCaseWizardState.handoffDescription}
                  onChange={(event) => setUseCaseField("handoffDescription", event.target.value)}
                />
              </label>
              <label>
                {t("useCasesPage.formRouting")}
                <span className="helper" style={{ fontSize: "0.78rem", fontWeight: 400 }}>
                  {t("useCasesPage.formRoutingHelp")}
                </span>
                <textarea
                  rows={3}
                  value={useCaseWizardState.routingDescription}
                  onChange={(event) => setUseCaseField("routingDescription", event.target.value)}
                />
              </label>
              <label>
                {t("useCasesPage.formRequiredFields")}
                <input
                  value={useCaseWizardState.requiredFieldsText}
                  onChange={(event) => setUseCaseField("requiredFieldsText", event.target.value)}
                />
              </label>
            </div>
          ) : null}

          {useCaseWizardStep === 3 ? (
            <div>
              <p className="helper">{t("useCasesPage.workflowTitle")}</p>
              <div className="step-list">
                {useCaseWizardState.steps.map((step, index) => (
                  <article key={`${step.step_id}-${index}`} className="step-item">
                    <label>
                      {t("useCasesPage.workflowStep")}
                      <select
                        value={step.step_id}
                        onChange={(event) =>
                          updateUseCaseStepAt(index, (previous) => ({
                            ...previous,
                            step_id: event.target.value,
                          }))
                        }
                      >
                        {selectedUseCaseAllowedSteps.map((stepId) => (
                          <option key={stepId} value={stepId}>
                            {STEP_LABELS[stepId] ?? stepId}
                          </option>
                        ))}
                      </select>
                    </label>

                    {(step.step_id === "append_resolution_note" ||
                      step.step_id === "manual_instruction") && (
                      <label>
                        {step.step_id === "append_resolution_note"
                          ? t("useCasesPage.workflowNote")
                          : t("useCasesPage.workflowInstruction")}
                        <input
                          value={
                            step.step_id === "append_resolution_note"
                              ? String(step.params.note ?? "")
                              : String(step.params.instruction ?? "")
                          }
                          onChange={(event) =>
                            updateUseCaseStepAt(index, (previous) => ({
                              ...previous,
                              params:
                                step.step_id === "append_resolution_note"
                                  ? { ...previous.params, note: event.target.value }
                                  : { ...previous.params, instruction: event.target.value },
                            }))
                          }
                        />
                      </label>
                    )}

                    <div className="step-actions">
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => moveUseCaseStep(index, -1)}
                      >
                        {t("useCasesPage.workflowUp")}
                      </button>
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => moveUseCaseStep(index, 1)}
                      >
                        {t("useCasesPage.workflowDown")}
                      </button>
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => removeUseCaseStep(index)}
                      >
                        {t("useCasesPage.workflowRemove")}
                      </button>
                    </div>
                  </article>
                ))}
              </div>
              <button type="button" className="ghost" onClick={addUseCaseStep}>
                {t("useCasesPage.workflowAddStep")}
              </button>
            </div>
          ) : null}

          {useCaseWizardStep === 4 ? (
            <div className="review-box">
              <h4>{t("useCasesPage.reviewTitle")}</h4>
              <p>
                <strong>{t("useCasesPage.reviewDisplay")}:</strong> {useCaseWizardState.displayName}
              </p>
              <p>
                <strong>{t("useCasesPage.reviewCategory")}:</strong>{" "}
                {useCaseWizardState.categoryId || t("common.none")}
              </p>
              <p>
                <strong>{t("useCasesPage.reviewRequiredFields")}:</strong>{" "}
                {useCaseWizardState.requiredFieldsText}
              </p>
              <p>
                <strong>{t("useCasesPage.reviewSteps")}:</strong>{" "}
                {useCaseWizardState.steps.map((step) => step.step_id).join(" -> ")}
              </p>
            </div>
          ) : null}
        </WizardModal>
      ) : null}
    </section>
  );
}
