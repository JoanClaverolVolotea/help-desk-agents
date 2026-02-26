import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import AdminTable from "../components/AdminTable";
import Breadcrumb from "../components/Breadcrumb";
import WizardModal from "../components/WizardModal";
import { useI18n } from "../../../shared/i18n/useI18n";
import { readableError } from "../../../shared/api/errors";
import {
  archiveCategory,
  createCategory,
  getCategory,
  listCategories,
  listSteps,
  listUseCases,
  migrateUseCaseCategoryVersion,
  publishCategory,
  reseedDefaults,
  restoreCategory,
  updateCategoryDraft,
} from "../api/adminCatalogClient";
import {
  type CategoryWizardState,
  STEP_LABELS,
  buildCategoryPayload,
  categoryWizardFromDetail,
  defaultCategoryWizard,
  parseValidationError,
} from "../utils/adminPayloads";
import type {
  CategoryDetail,
  CategorySummary,
  StepDefinition,
  UseCaseSummary,
} from "../types";

type CategoryRow = CategorySummary & { id: string };

interface MigrationPromptItem {
  use_case_id: string;
  display_name: string;
  selected: boolean;
}

interface MigrationPrompt {
  categoryId: string;
  categoryVersionNumber: number | null;
  items: MigrationPromptItem[];
}

interface StepOption {
  stepId: string;
  label: string;
  searchText: string;
}

export default function ITAdminCategoriesPage(): JSX.Element {
  const { t } = useI18n();
  const [steps, setSteps] = useState<StepDefinition[]>([]);
  const [categories, setCategories] = useState<CategorySummary[]>([]);
  const [includeArchivedCategories, setIncludeArchivedCategories] = useState(false);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminError, setAdminError] = useState("");
  const [categoryPublishNotice, setCategoryPublishNotice] = useState("");
  const [reseedBusy, setReseedBusy] = useState(false);
  const [useCaseCounts, setUseCaseCounts] = useState<Record<string, number>>({});

  const [showCategoryWizard, setShowCategoryWizard] = useState(false);
  const [categoryWizardMode, setCategoryWizardMode] = useState<"create" | "edit">("create");
  const [categoryWizardStep, setCategoryWizardStep] = useState(1);
  const [categoryWizardBusy, setCategoryWizardBusy] = useState(false);
  const [categoryWizardError, setCategoryWizardError] = useState("");
  const [categoryWizardState, setCategoryWizardState] = useState<CategoryWizardState | null>(null);
  const [allowedStepSearch, setAllowedStepSearch] = useState("");
  const [defaultStepSearch, setDefaultStepSearch] = useState("");

  const [migrationPrompt, setMigrationPrompt] = useState<MigrationPrompt | null>(null);

  const loadAdminData = async (): Promise<void> => {
    setAdminLoading(true);
    setAdminError("");

    try {
      const [stepsResponse, categoriesResponse, useCasesResponse] = await Promise.all([
        listSteps(),
        listCategories(includeArchivedCategories),
        listUseCases(true),
      ]);
      setSteps(stepsResponse.items);
      setCategories(categoriesResponse.items);

      const counts: Record<string, number> = {};
      for (const useCase of useCasesResponse.items as UseCaseSummary[]) {
        if (useCase.category_id) {
          counts[useCase.category_id] = (counts[useCase.category_id] || 0) + 1;
        }
      }
      setUseCaseCounts(counts);
    } catch (error) {
      setAdminError(readableError(error));
    } finally {
      setAdminLoading(false);
    }
  };

  useEffect(() => {
    void loadAdminData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [includeArchivedCategories]);

  const openCreateCategoryWizard = (): void => {
    setCategoryWizardMode("create");
    setCategoryWizardStep(1);
    setCategoryWizardError("");
    setAllowedStepSearch("");
    setDefaultStepSearch("");
    setCategoryWizardState(defaultCategoryWizard(steps));
    setShowCategoryWizard(true);
  };

  const openEditCategoryWizard = async (categoryId: string): Promise<void> => {
    setCategoryWizardBusy(true);
    setCategoryWizardError("");

    try {
      const response = await getCategory(categoryId);
      const wizard = categoryWizardFromDetail(response.category);
      if (!wizard) {
        throw new Error(t("categoriesPage.noDefinition"));
      }

      setCategoryWizardMode("edit");
      setCategoryWizardStep(1);
      setAllowedStepSearch("");
      setDefaultStepSearch("");
      setCategoryWizardState(wizard);
      setShowCategoryWizard(true);
    } catch (error) {
      setCategoryWizardError(readableError(error));
    } finally {
      setCategoryWizardBusy(false);
    }
  };

  const closeCategoryWizard = (): void => {
    setShowCategoryWizard(false);
    setCategoryWizardState(null);
    setCategoryWizardStep(1);
    setCategoryWizardError("");
    setAllowedStepSearch("");
    setDefaultStepSearch("");
  };

  const setCategoryField = <K extends keyof CategoryWizardState>(
    key: K,
    value: CategoryWizardState[K],
  ): void => {
    setCategoryWizardState((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  const toggleCategoryStep = (
    stepId: string,
    key: "allowedStepIds" | "defaultStepIds" = "allowedStepIds",
  ): void => {
    setCategoryWizardState((prev) => {
      if (!prev) {
        return prev;
      }

      const selected = prev[key].includes(stepId);
      const nextValues = selected ? prev[key].filter((item) => item !== stepId) : [...prev[key], stepId];

      if (key === "allowedStepIds") {
        const allowedSet = new Set(nextValues);
        return {
          ...prev,
          allowedStepIds: nextValues,
          defaultStepIds: prev.defaultStepIds.filter((item) => allowedSet.has(item)),
        };
      }

      return { ...prev, [key]: nextValues };
    });
  };

  const addVisibleAllowedSteps = (stepIds: string[]): void => {
    setCategoryWizardState((prev) => {
      if (!prev) {
        return prev;
      }
      const allowedSet = new Set(prev.allowedStepIds);
      for (const stepId of stepIds) {
        allowedSet.add(stepId);
      }
      return { ...prev, allowedStepIds: Array.from(allowedSet) };
    });
  };

  const clearVisibleAllowedSteps = (stepIds: string[]): void => {
    setCategoryWizardState((prev) => {
      if (!prev) {
        return prev;
      }
      const toRemove = new Set(stepIds);
      const allowedStepIds = prev.allowedStepIds.filter((stepId) => !toRemove.has(stepId));
      const allowedSet = new Set(allowedStepIds);
      return {
        ...prev,
        allowedStepIds,
        defaultStepIds: prev.defaultStepIds.filter((stepId) => allowedSet.has(stepId)),
      };
    });
  };

  const addVisibleDefaultSteps = (stepIds: string[]): void => {
    setCategoryWizardState((prev) => {
      if (!prev) {
        return prev;
      }
      const defaultSet = new Set(prev.defaultStepIds);
      const allowedSet = new Set(prev.allowedStepIds);
      for (const stepId of stepIds) {
        if (allowedSet.has(stepId)) {
          defaultSet.add(stepId);
        }
      }
      return { ...prev, defaultStepIds: Array.from(defaultSet) };
    });
  };

  const clearVisibleDefaultSteps = (stepIds: string[]): void => {
    setCategoryWizardState((prev) => {
      if (!prev) {
        return prev;
      }
      const toRemove = new Set(stepIds);
      return {
        ...prev,
        defaultStepIds: prev.defaultStepIds.filter((stepId) => !toRemove.has(stepId)),
      };
    });
  };

  const stepOptions = useMemo<StepOption[]>(
    () =>
      steps.map((step) => {
        const label = STEP_LABELS[step.step_id] ?? step.step_id;
        return {
          stepId: step.step_id,
          label,
          searchText: `${label} ${step.step_id}`.toLowerCase(),
        };
      }),
    [steps],
  );

  const allowedSearchValue = allowedStepSearch.trim().toLowerCase();
  const defaultSearchValue = defaultStepSearch.trim().toLowerCase();
  const allowedStepIds = categoryWizardState?.allowedStepIds ?? [];
  const defaultStepIds = categoryWizardState?.defaultStepIds ?? [];

  const filteredAllowedStepOptions = useMemo(
    () => stepOptions.filter((option) => !allowedSearchValue || option.searchText.includes(allowedSearchValue)),
    [allowedSearchValue, stepOptions],
  );

  const defaultStepOptions = useMemo(() => {
    const allowedSet = new Set(allowedStepIds);
    return stepOptions.filter((option) => allowedSet.has(option.stepId));
  }, [allowedStepIds, stepOptions]);

  const filteredDefaultStepOptions = useMemo(
    () => defaultStepOptions.filter((option) => !defaultSearchValue || option.searchText.includes(defaultSearchValue)),
    [defaultSearchValue, defaultStepOptions],
  );

  const validateCategoryWizard = (wizardState: CategoryWizardState): string => {
    if (!wizardState.displayName.trim()) {
      return t("categoriesPage.validationDisplayName");
    }
    if (!wizardState.description.trim()) {
      return t("categoriesPage.validationDescription");
    }
    if (!wizardState.defaultHandoffDescription.trim()) {
      return t("categoriesPage.validationHandoff");
    }
    if (!wizardState.defaultRoutingDescription.trim()) {
      return t("categoriesPage.validationRouting");
    }
    if (wizardState.allowedStepIds.length === 0) {
      return t("categoriesPage.validationAllowed");
    }
    if (wizardState.defaultStepIds.length === 0) {
      return t("categoriesPage.validationDefault");
    }
    return "";
  };

  const saveCategoryDraft = async (): Promise<CategoryDetail | null> => {
    if (!categoryWizardState) {
      return null;
    }

    const validationError = validateCategoryWizard(categoryWizardState);
    if (validationError) {
      setCategoryWizardError(validationError);
      return null;
    }

    setCategoryWizardBusy(true);
    setCategoryWizardError("");

    try {
      if (categoryWizardState.categoryId) {
        const response = await updateCategoryDraft(
          categoryWizardState.categoryId,
          buildCategoryPayload(categoryWizardState),
        );
        await loadAdminData();
        return response.category;
      }

      const response = await createCategory(buildCategoryPayload(categoryWizardState));
      setCategoryWizardState((prev) =>
        prev ? { ...prev, categoryId: response.category.category_id } : prev,
      );
      await loadAdminData();
      return response.category;
    } catch (error) {
      setCategoryWizardError(parseValidationError(readableError(error)));
      return null;
    } finally {
      setCategoryWizardBusy(false);
    }
  };

  const publishCategoryAndPromptMigration = async (categoryId: string): Promise<void> => {
    setAdminError("");
    setCategoryPublishNotice("");

    try {
      const response = await publishCategory(categoryId);
      await loadAdminData();

      setCategoryPublishNotice(t("categoriesPage.publishedNotice"));

      const latestUseCases = await listUseCases(false);
      const affected = latestUseCases.items.filter(
        (item) =>
          item.category_id === categoryId &&
          item.published_version_number !== null &&
          !item.archived &&
          !item.is_system_default,
      );

      if (affected.length > 0) {
        setMigrationPrompt({
          categoryId,
          categoryVersionNumber: response.category.published_version_number,
          items: affected.map((item) => ({
            use_case_id: item.use_case_id,
            display_name: item.display_name,
            selected: true,
          })),
        });
      }
    } catch (error) {
      setCategoryPublishNotice("");
      setAdminError(readableError(error));
    }
  };

  const publishCategoryFromWizard = async (): Promise<void> => {
    const saved = await saveCategoryDraft();
    if (!saved) {
      return;
    }
    await publishCategoryAndPromptMigration(saved.category_id);
    closeCategoryWizard();
  };

  const archiveCategoryFromList = async (categoryId: string): Promise<void> => {
    setAdminError("");

    try {
      await archiveCategory(categoryId);
      await loadAdminData();
    } catch (error) {
      setAdminError(readableError(error));
    }
  };

  const restoreCategoryFromList = async (categoryId: string): Promise<void> => {
    setAdminError("");

    try {
      await restoreCategory(categoryId);
      await loadAdminData();
    } catch (error) {
      setAdminError(readableError(error));
    }
  };

  const runMigration = async (): Promise<void> => {
    if (!migrationPrompt) {
      return;
    }

    const selectedItems = migrationPrompt.items.filter((item) => item.selected);
    if (selectedItems.length === 0) {
      setMigrationPrompt(null);
      return;
    }

    setAdminError("");

    try {
      await Promise.all(
        selectedItems.map((item) =>
          migrateUseCaseCategoryVersion(item.use_case_id, {
            category_id: migrationPrompt.categoryId,
            category_version_number: migrationPrompt.categoryVersionNumber,
          }),
        ),
      );
      setMigrationPrompt(null);
      await loadAdminData();
    } catch (error) {
      setAdminError(readableError(error));
    }
  };

  const handleReseedDefaults = async (): Promise<void> => {
    const confirmed = window.confirm(t("categoriesPage.reseedConfirm"));
    if (!confirmed) {
      return;
    }

    setReseedBusy(true);
    setAdminError("");
    setCategoryPublishNotice("");
    setMigrationPrompt(null);

    try {
      const response = await reseedDefaults();
      await loadAdminData();
      const useCasesResponse = await listUseCases(false);
      setCategoryPublishNotice(
        t("categoriesPage.reseedNotice", {
          tickets: response.deleted_counts.tickets,
          useCases: response.deleted_counts.use_cases,
          categories: response.deleted_counts.categories,
          seededCategories: response.seeded_counts.categories,
          seededUseCases: response.seeded_counts.use_cases,
          activeUseCases: useCasesResponse.items.length,
        }),
      );
    } catch (error) {
      setAdminError(readableError(error));
    } finally {
      setReseedBusy(false);
    }
  };

  return (
    <section className="tab-panel admin-panel it-console-panel it-console-categories">
      <Breadcrumb
        items={[
          { label: t("common.dashboard"), to: "/it/dashboard" },
          { label: t("common.categories") },
        ]}
      />
      <div className="admin-toolbar">
        <h2>{t("categoriesPage.heading")}</h2>
        <div className="admin-toolbar-actions">
          <button type="button" className="ghost" onClick={() => void loadAdminData()} disabled={adminLoading}>
            {t("common.refresh")}
          </button>
          <button
            type="button"
            className="ghost"
            onClick={() => void handleReseedDefaults()}
            disabled={adminLoading || reseedBusy}
          >
            {t("categoriesPage.reseedDefaults")}
          </button>
          <button type="button" className="primary" onClick={openCreateCategoryWizard}>
            {t("categoriesPage.create")}
          </button>
        </div>
      </div>

      <label className="toggle-row">
        <input
          type="checkbox"
          checked={includeArchivedCategories}
          onChange={(event) => setIncludeArchivedCategories(event.target.checked)}
        />
        <span>{t("common.showArchived")}</span>
      </label>
      <section className="console-clarity-card">
        <h3>{t("categoriesPage.cardTitle")}</h3>
        <p>{t("categoriesPage.cardBody")}</p>
      </section>

      {adminLoading ? <p className="helper">{t("common.loadingData")}</p> : null}
      {categoryPublishNotice ? <p className="helper">{categoryPublishNotice}</p> : null}
      {adminError ? <p className="error-text">{adminError}</p> : null}

      {migrationPrompt ? (
        <section className="migration-box">
          <h3>{t("categoriesPage.migrationTitle")}</h3>
          <p>{t("categoriesPage.migrationBody", { version: migrationPrompt.categoryVersionNumber ?? 0 })}</p>
          <p className="helper">
            {t("categoriesPage.migrationHelp")} <Link to="/it/admin/use-cases">{t("common.runbooks")}</Link>.
          </p>
          <div className="check-grid">
            {migrationPrompt.items.map((item, index) => (
              <label key={item.use_case_id} className="check-item">
                <input
                  type="checkbox"
                  checked={item.selected}
                  onChange={() =>
                    setMigrationPrompt((prev) => {
                      if (!prev) {
                        return prev;
                      }
                      const items = [...prev.items];
                      items[index] = { ...items[index], selected: !items[index].selected };
                      return { ...prev, items };
                    })
                  }
                />
                <span>{item.display_name}</span>
              </label>
            ))}
          </div>
          <div className="wizard-submit">
            <button type="button" className="ghost" onClick={() => setMigrationPrompt(null)}>
              {t("categoriesPage.migrationSkip")}
            </button>
            <button type="button" className="primary" onClick={() => void runMigration()}>
              {t("categoriesPage.migrationApply")}
            </button>
          </div>
        </section>
      ) : null}

      <AdminTable<CategoryRow>
        columns={[
          {
            key: "name",
            label: t("categoriesPage.tableName"),
            render: (row) => <strong>{row.display_name}</strong>,
          },
          {
            key: "status",
            label: t("categoriesPage.tableStatus"),
            render: (row) => (
              <div className="badge-row">
                <span className={row.archived ? "badge archived" : "badge published"}>
                  {row.archived ? t("common.archived") : t("common.active")}
                </span>
                {row.draft_version_number ? (
                  <span className="badge draft">{t("common.unpublishedChanges")}</span>
                ) : null}
              </div>
            ),
          },
          {
            key: "use_cases",
            label: t("categoriesPage.tableRunbooks"),
            render: (row) => (
              <Link to={`/it/admin/use-cases?category_id=${row.category_id}`}>
                {useCaseCounts[row.category_id] || 0}
              </Link>
            ),
          },
          {
            key: "actions",
            label: "",
            render: (row) => (
              <div className="use-case-actions" style={{ flexDirection: "row" }}>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => void openEditCategoryWizard(row.category_id)}
                >
                  {t("common.edit")}
                </button>
                <button
                  type="button"
                  className="primary"
                  disabled={!row.draft_version_number || row.archived}
                  onClick={() => void publishCategoryAndPromptMigration(row.category_id)}
                >
                  {t("common.publish")}
                </button>
                {row.archived ? (
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => void restoreCategoryFromList(row.category_id)}
                  >
                    {t("common.restore")}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => void archiveCategoryFromList(row.category_id)}
                  >
                    {t("common.archive")}
                  </button>
                )}
              </div>
            ),
          },
        ]}
        rows={categories.map((item) => ({ ...item, id: item.category_id }))}
        emptyMessage={t("categoriesPage.emptyCategories")}
      />

      {showCategoryWizard && categoryWizardState ? (
        <WizardModal
          title={categoryWizardMode === "create" ? t("categoriesPage.wizardNew") : t("categoriesPage.wizardEdit")}
          step={categoryWizardStep}
          totalSteps={4}
          onClose={closeCategoryWizard}
          error={categoryWizardError}
          navActions={
            <>
              <button
                type="button"
                className="ghost"
                onClick={() => setCategoryWizardStep((prev) => Math.max(1, prev - 1))}
                disabled={categoryWizardStep === 1}
              >
                {t("common.previous")}
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => setCategoryWizardStep((prev) => Math.min(4, prev + 1))}
                disabled={categoryWizardStep === 4}
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
                onClick={() => void saveCategoryDraft()}
                disabled={categoryWizardBusy}
              >
                {t("common.saveDraft")}
              </button>
              <button
                type="button"
                className="primary"
                onClick={() => void publishCategoryFromWizard()}
                disabled={categoryWizardBusy}
              >
                {t("common.saveAndPublish")}
              </button>
            </>
          }
        >
          {categoryWizardStep === 1 ? (
            <div className="form-grid">
              <label>
                {t("categoriesPage.formDisplayName")}
                <input
                  value={categoryWizardState.displayName}
                  onChange={(event) => setCategoryField("displayName", event.target.value)}
                />
              </label>
              <label>
                {t("categoriesPage.formSlug")}
                <span className="helper" style={{ fontSize: "0.78rem", fontWeight: 400 }}>
                  {t("categoriesPage.formSlugHelp")}
                </span>
                <input
                  value={categoryWizardState.slug}
                  onChange={(event) => setCategoryField("slug", event.target.value)}
                />
              </label>
              <label>
                {t("categoriesPage.formDescription")}
                <textarea
                  rows={3}
                  value={categoryWizardState.description}
                  onChange={(event) => setCategoryField("description", event.target.value)}
                />
              </label>
            </div>
          ) : null}

          {categoryWizardStep === 2 ? (
            <div className="step-selector-section">
              <p className="helper">{t("categoriesPage.stepAllowedTitle")}.</p>
              <p className="helper step-helper-copy">{t("categoriesPage.stepAllowedHelp")}</p>
              <div className="step-selector-toolbar">
                <input
                  type="search"
                  value={allowedStepSearch}
                  onChange={(event) => setAllowedStepSearch(event.target.value)}
                  placeholder={t("categoriesPage.stepAllowedSearchPlaceholder")}
                />
                <div className="step-selector-actions">
                  <span className="helper">
                    {t("categoriesPage.stepAllowedCount", {
                      selected: allowedStepIds.length,
                      total: steps.length,
                    })}
                  </span>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() =>
                      addVisibleAllowedSteps(filteredAllowedStepOptions.map((option) => option.stepId))
                    }
                    disabled={filteredAllowedStepOptions.length === 0}
                  >
                    {t("categoriesPage.stepSelectVisible")}
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() =>
                      clearVisibleAllowedSteps(filteredAllowedStepOptions.map((option) => option.stepId))
                    }
                    disabled={filteredAllowedStepOptions.length === 0}
                  >
                    {t("categoriesPage.stepClearVisible")}
                  </button>
                </div>
              </div>
              {filteredAllowedStepOptions.length === 0 ? (
                <p className="helper step-selector-empty">{t("categoriesPage.stepNoMatch")}</p>
              ) : (
                <div className="check-grid step-selector-grid">
                  {filteredAllowedStepOptions.map((option) => (
                    <label key={option.stepId} className="check-item">
                      <input
                        type="checkbox"
                        checked={allowedStepIds.includes(option.stepId)}
                        onChange={() => toggleCategoryStep(option.stepId, "allowedStepIds")}
                      />
                      <span>{option.label}</span>
                    </label>
                  ))}
                </div>
              )}

              <p className="helper">{t("categoriesPage.stepDefaultTitle")}.</p>
              <p className="helper step-helper-copy">{t("categoriesPage.stepDefaultHelp")}</p>
              <div className="step-selector-toolbar">
                <input
                  type="search"
                  value={defaultStepSearch}
                  onChange={(event) => setDefaultStepSearch(event.target.value)}
                  placeholder={t("categoriesPage.stepDefaultSearchPlaceholder")}
                  disabled={defaultStepOptions.length === 0}
                />
                <div className="step-selector-actions">
                  <span className="helper">
                    {t("categoriesPage.stepDefaultCount", {
                      selected: defaultStepIds.length,
                      total: defaultStepOptions.length,
                    })}
                  </span>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() =>
                      addVisibleDefaultSteps(filteredDefaultStepOptions.map((option) => option.stepId))
                    }
                    disabled={filteredDefaultStepOptions.length === 0}
                  >
                    {t("categoriesPage.stepSelectVisible")}
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() =>
                      clearVisibleDefaultSteps(filteredDefaultStepOptions.map((option) => option.stepId))
                    }
                    disabled={filteredDefaultStepOptions.length === 0}
                  >
                    {t("categoriesPage.stepClearVisible")}
                  </button>
                </div>
              </div>
              {defaultStepOptions.length === 0 ? (
                <p className="helper step-selector-empty">{t("categoriesPage.stepNoDefaultsSource")}</p>
              ) : filteredDefaultStepOptions.length === 0 ? (
                <p className="helper step-selector-empty">{t("categoriesPage.stepNoDefaultMatch")}</p>
              ) : (
                <div className="check-grid step-selector-grid">
                  {filteredDefaultStepOptions.map((option) => (
                    <label key={option.stepId} className="check-item">
                      <input
                        type="checkbox"
                        checked={defaultStepIds.includes(option.stepId)}
                        onChange={() => toggleCategoryStep(option.stepId, "defaultStepIds")}
                      />
                      <span>{option.label}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          ) : null}

          {categoryWizardStep === 3 ? (
            <div className="form-grid">
              <label>
                {t("categoriesPage.formHandoff")}
                <span className="helper" style={{ fontSize: "0.78rem", fontWeight: 400 }}>
                  {t("categoriesPage.formHandoffHelp")}
                </span>
                <textarea
                  rows={3}
                  value={categoryWizardState.defaultHandoffDescription}
                  onChange={(event) =>
                    setCategoryField("defaultHandoffDescription", event.target.value)
                  }
                />
              </label>
              <label>
                {t("categoriesPage.formRouting")}
                <span className="helper" style={{ fontSize: "0.78rem", fontWeight: 400 }}>
                  {t("categoriesPage.formRoutingHelp")}
                </span>
                <textarea
                  rows={3}
                  value={categoryWizardState.defaultRoutingDescription}
                  onChange={(event) =>
                    setCategoryField("defaultRoutingDescription", event.target.value)
                  }
                />
              </label>
              <label>
                {t("categoriesPage.formRequiredFields")}
                <span className="helper" style={{ fontSize: "0.78rem", fontWeight: 400 }}>
                  {t("categoriesPage.formRequiredFieldsHelp")}
                </span>
                <input
                  value={categoryWizardState.defaultRequiredFieldsText}
                  onChange={(event) =>
                    setCategoryField("defaultRequiredFieldsText", event.target.value)
                  }
                />
              </label>
            </div>
          ) : null}

          {categoryWizardStep === 4 ? (
            <div className="review-box">
              <h4>{t("categoriesPage.reviewTitle")}</h4>
              <p>
                <strong>{t("categoriesPage.reviewDisplay")}:</strong> {categoryWizardState.displayName}
              </p>
              <p>
                <strong>{t("categoriesPage.reviewSlug")}:</strong>{" "}
                {categoryWizardState.slug || `(${t("common.auto")})`}
              </p>
              <p>
                <strong>{t("categoriesPage.reviewAllowed")}:</strong>{" "}
                {categoryWizardState.allowedStepIds.join(", ")}
              </p>
              <p>
                <strong>{t("categoriesPage.reviewDefault")}:</strong>{" "}
                {categoryWizardState.defaultStepIds.join(", ")}
              </p>
              <p>
                <strong>{t("categoriesPage.reviewDefaultFields")}:</strong>{" "}
                {categoryWizardState.defaultRequiredFieldsText}
              </p>
            </div>
          ) : null}
        </WizardModal>
      ) : null}
    </section>
  );
}
