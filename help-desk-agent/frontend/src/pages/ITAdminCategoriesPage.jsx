import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import AdminTable from "../components/AdminTable.jsx";
import Breadcrumb from "../components/Breadcrumb.jsx";
import WizardModal from "../components/WizardModal.jsx";
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
  readableError,
  restoreCategory,
  updateCategoryDraft,
} from "../api.js";
import {
  STEP_LABELS,
  buildCategoryPayload,
  categoryWizardFromDetail,
  defaultCategoryWizard,
  parseValidationError,
} from "../utils/adminPayloads.js";

export default function ITAdminCategoriesPage() {
  const [steps, setSteps] = useState([]);
  const [categories, setCategories] = useState([]);
  const [includeArchivedCategories, setIncludeArchivedCategories] = useState(false);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminError, setAdminError] = useState("");
  const [categoryPublishNotice, setCategoryPublishNotice] = useState("");
  const [reseedBusy, setReseedBusy] = useState(false);
  const [useCaseCounts, setUseCaseCounts] = useState({});

  const [showCategoryWizard, setShowCategoryWizard] = useState(false);
  const [categoryWizardMode, setCategoryWizardMode] = useState("create");
  const [categoryWizardStep, setCategoryWizardStep] = useState(1);
  const [categoryWizardBusy, setCategoryWizardBusy] = useState(false);
  const [categoryWizardError, setCategoryWizardError] = useState("");
  const [categoryWizardState, setCategoryWizardState] = useState(null);

  const [migrationPrompt, setMigrationPrompt] = useState(null);

  const loadAdminData = async () => {
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

      const counts = {};
      for (const uc of useCasesResponse.items) {
        if (uc.category_id) {
          counts[uc.category_id] = (counts[uc.category_id] || 0) + 1;
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
    loadAdminData();
  }, [includeArchivedCategories]);

  const openCreateCategoryWizard = () => {
    setCategoryWizardMode("create");
    setCategoryWizardStep(1);
    setCategoryWizardError("");
    setCategoryWizardState(defaultCategoryWizard(steps));
    setShowCategoryWizard(true);
  };

  const openEditCategoryWizard = async (categoryId) => {
    setCategoryWizardBusy(true);
    setCategoryWizardError("");

    try {
      const response = await getCategory(categoryId);
      const wizard = categoryWizardFromDetail(response.category);
      if (!wizard) {
        throw new Error("Category has no draft or published definition.");
      }

      setCategoryWizardMode("edit");
      setCategoryWizardStep(1);
      setCategoryWizardState(wizard);
      setShowCategoryWizard(true);
    } catch (error) {
      setCategoryWizardError(readableError(error));
    } finally {
      setCategoryWizardBusy(false);
    }
  };

  const closeCategoryWizard = () => {
    setShowCategoryWizard(false);
    setCategoryWizardState(null);
    setCategoryWizardStep(1);
    setCategoryWizardError("");
  };

  const setCategoryField = (key, value) => {
    setCategoryWizardState((prev) => ({ ...prev, [key]: value }));
  };

  const toggleCategoryStep = (stepId, key = "allowedStepIds") => {
    setCategoryWizardState((prev) => {
      const selected = prev[key].includes(stepId);
      return {
        ...prev,
        [key]: selected ? prev[key].filter((item) => item !== stepId) : [...prev[key], stepId],
      };
    });
  };

  const validateCategoryWizard = (wizardState) => {
    if (!wizardState.displayName.trim()) {
      return "Nombre de categoria obligatorio. / Category display name is required.";
    }
    if (!wizardState.description.trim()) {
      return "Descripcion obligatoria. / Description is required.";
    }
    if (!wizardState.defaultHandoffDescription.trim()) {
      return "Handoff description is required.";
    }
    if (!wizardState.defaultRoutingDescription.trim()) {
      return "Routing description is required.";
    }
    if (wizardState.allowedStepIds.length === 0) {
      return "Selecciona al menos un paso permitido. / Select at least one allowed step.";
    }
    if (wizardState.defaultStepIds.length === 0) {
      return "Selecciona al menos un paso por defecto. / Select at least one default step.";
    }
    return "";
  };

  const saveCategoryDraft = async () => {
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
      setCategoryWizardState((prev) => ({ ...prev, categoryId: response.category.category_id }));
      await loadAdminData();
      return response.category;
    } catch (error) {
      setCategoryWizardError(parseValidationError(readableError(error)));
      return null;
    } finally {
      setCategoryWizardBusy(false);
    }
  };

  const publishCategoryAndPromptMigration = async (categoryId) => {
    setAdminError("");
    setCategoryPublishNotice("");

    try {
      const response = await publishCategory(categoryId);
      await loadAdminData();

      setCategoryPublishNotice(
        "Caso predeterminado sincronizado y disponible en el chat de usuario. / Default use-case synced and available in user chat.",
      );

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

  const publishCategoryFromWizard = async () => {
    const saved = await saveCategoryDraft();
    if (!saved) {
      return;
    }
    await publishCategoryAndPromptMigration(saved.category_id);
    closeCategoryWizard();
  };

  const archiveCategoryFromList = async (categoryId) => {
    setAdminError("");

    try {
      await archiveCategory(categoryId);
      await loadAdminData();
    } catch (error) {
      setAdminError(readableError(error));
    }
  };

  const restoreCategoryFromList = async (categoryId) => {
    setAdminError("");

    try {
      await restoreCategory(categoryId);
      await loadAdminData();
    } catch (error) {
      setAdminError(readableError(error));
    }
  };

  const runMigration = async () => {
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

  const handleReseedDefaults = async () => {
    const confirmed = window.confirm(
      "This action deletes current categories, use-cases, and ticket registry data, then reseeds defaults. Continue?",
    );
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
        `Defaults reseeded. Deleted tickets/use-cases/categories: ${response.deleted_counts.tickets}/${response.deleted_counts.use_cases}/${response.deleted_counts.categories}. Seeded categories/use-cases: ${response.seeded_counts.categories}/${response.seeded_counts.use_cases}. Active use-cases now: ${useCasesResponse.items.length}.`,
      );
    } catch (error) {
      setAdminError(readableError(error));
    } finally {
      setReseedBusy(false);
    }
  };

  return (
    <section className="tab-panel admin-panel it-console-panel it-console-categories">
      <Breadcrumb items={[{ label: "Dashboard", to: "/it/dashboard" }, { label: "Categories" }]} />
      <div className="admin-toolbar">
        <h2>Categories / Categorías</h2>
        <div className="admin-toolbar-actions">
          <button type="button" className="ghost" onClick={loadAdminData} disabled={adminLoading}>
            Refresh
          </button>
          <button
            type="button"
            className="ghost"
            onClick={handleReseedDefaults}
            disabled={adminLoading || reseedBusy}
          >
            Reseed defaults
          </button>
          <button type="button" className="primary" onClick={openCreateCategoryWizard}>
            Nueva categoría
          </button>
        </div>
      </div>

      <label className="toggle-row">
        <input
          type="checkbox"
          checked={includeArchivedCategories}
          onChange={(event) => setIncludeArchivedCategories(event.target.checked)}
        />
        <span>Mostrar archivadas / Show archived</span>
      </label>
      <section className="console-clarity-card">
        <h3>What are Categories?</h3>
        <p>
          Categories group related issues (e.g. "Network", "Software"). Each category defines what
          steps are available and automatically creates a default runbook. When you publish changes,
          linked runbooks can be updated too.
        </p>
      </section>

      {adminLoading ? <p className="helper">Cargando datos...</p> : null}
      {categoryPublishNotice ? <p className="helper">{categoryPublishNotice}</p> : null}
      {adminError ? <p className="error-text">{adminError}</p> : null}

      {migrationPrompt ? (
        <section className="migration-box">
          <h3>Migracion sugerida / Suggested migration</h3>
          <p>
            Categoria publicada con version <strong>{migrationPrompt.categoryVersionNumber}</strong>.
            Selecciona los casos a migrar.
          </p>
          <p className="helper">
            This is a cross-entity action on linked use-cases. Review list/details in{" "}
            <Link to="/it/admin/use-cases">Runbooks</Link>.
          </p>
          <div className="check-grid">
            {migrationPrompt.items.map((item, index) => (
              <label key={item.use_case_id} className="check-item">
                <input
                  type="checkbox"
                  checked={item.selected}
                  onChange={() =>
                    setMigrationPrompt((prev) => {
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
              Omitir
            </button>
            <button type="button" className="primary" onClick={runMigration}>
              Migrar seleccionados
            </button>
          </div>
        </section>
      ) : null}

      <AdminTable
        columns={[
          { key: "name", label: "Name", render: (row) => (
            <strong>{row.display_name}</strong>
          )},
          { key: "status", label: "Status", render: (row) => (
            <div className="badge-row">
              <span className={row.archived ? "badge archived" : "badge published"}>
                {row.archived ? "Archived" : "Active"}
              </span>
              {row.draft_version_number ? (
                <span className="badge draft">Unpublished changes</span>
              ) : null}
            </div>
          )},
          { key: "use_cases", label: "Runbooks", render: (row) => (
            <Link to={`/it/admin/use-cases?category_id=${row.category_id}`}>
              {useCaseCounts[row.category_id] || 0}
            </Link>
          )},
          { key: "actions", label: "", render: (row) => (
            <div className="use-case-actions" style={{ flexDirection: "row" }}>
              <button type="button" className="ghost" onClick={() => openEditCategoryWizard(row.category_id)}>
                Edit
              </button>
              <button
                type="button"
                className="primary"
                disabled={!row.draft_version_number || row.archived}
                onClick={() => publishCategoryAndPromptMigration(row.category_id)}
              >
                Publish
              </button>
              {row.archived ? (
                <button type="button" className="ghost" onClick={() => restoreCategoryFromList(row.category_id)}>
                  Restore
                </button>
              ) : (
                <button type="button" className="ghost" onClick={() => archiveCategoryFromList(row.category_id)}>
                  Archive
                </button>
              )}
            </div>
          )},
        ]}
        rows={categories.map((item) => ({ ...item, id: item.category_id }))}
        emptyMessage="No categories yet."
      />

      {showCategoryWizard && categoryWizardState ? (
        <WizardModal
          title={categoryWizardMode === "create" ? "Nueva categoría" : "Editar categoría"}
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
                Anterior
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => setCategoryWizardStep((prev) => Math.min(4, prev + 1))}
                disabled={categoryWizardStep === 4}
              >
                Siguiente
              </button>
            </>
          }
          submitActions={
            <>
              <button
                type="button"
                className="ghost"
                onClick={saveCategoryDraft}
                disabled={categoryWizardBusy}
              >
                Guardar draft
              </button>
              <button
                type="button"
                className="primary"
                onClick={publishCategoryFromWizard}
                disabled={categoryWizardBusy}
              >
                Guardar y publicar
              </button>
            </>
          }
        >
          {categoryWizardStep === 1 ? (
            <div className="form-grid">
              <label>
                Nombre / Display name
                <input
                  value={categoryWizardState.displayName}
                  onChange={(event) => setCategoryField("displayName", event.target.value)}
                />
              </label>
              <label>
                Slug (optional)
                <span className="helper" style={{ fontSize: "0.78rem", fontWeight: 400 }}>
                  Short ID used in URLs and API calls. Auto-generated from the name if left blank.
                </span>
                <input
                  value={categoryWizardState.slug}
                  onChange={(event) => setCategoryField("slug", event.target.value)}
                />
              </label>
              <label>
                Descripcion
                <textarea
                  rows={3}
                  value={categoryWizardState.description}
                  onChange={(event) => setCategoryField("description", event.target.value)}
                />
              </label>
            </div>
          ) : null}

          {categoryWizardStep === 2 ? (
            <div>
              <p className="helper">Pasos permitidos / Allowed steps.</p>
              <div className="check-grid">
                {steps.map((step) => (
                  <label key={step.step_id} className="check-item">
                    <input
                      type="checkbox"
                      checked={categoryWizardState.allowedStepIds.includes(step.step_id)}
                      onChange={() => toggleCategoryStep(step.step_id, "allowedStepIds")}
                    />
                    <span>{STEP_LABELS[step.step_id] ?? step.step_id}</span>
                  </label>
                ))}
              </div>

              <p className="helper">Pasos por defecto / Default steps.</p>
              <div className="check-grid">
                {categoryWizardState.allowedStepIds.map((stepId) => (
                  <label key={stepId} className="check-item">
                    <input
                      type="checkbox"
                      checked={categoryWizardState.defaultStepIds.includes(stepId)}
                      onChange={() => toggleCategoryStep(stepId, "defaultStepIds")}
                    />
                    <span>{STEP_LABELS[stepId] ?? stepId}</span>
                  </label>
                ))}
              </div>
            </div>
          ) : null}

          {categoryWizardStep === 3 ? (
            <div className="form-grid">
              <label>
                Handoff description
                <textarea
                  rows={3}
                  value={categoryWizardState.defaultHandoffDescription}
                  onChange={(event) => setCategoryField("defaultHandoffDescription", event.target.value)}
                />
              </label>
              <label>
                Routing description
                <textarea
                  rows={3}
                  value={categoryWizardState.defaultRoutingDescription}
                  onChange={(event) => setCategoryField("defaultRoutingDescription", event.target.value)}
                />
              </label>
              <label>
                Default required fields (comma separated)
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
              <h4>Review</h4>
              <p>
                <strong>Display:</strong> {categoryWizardState.displayName}
              </p>
              <p>
                <strong>Slug:</strong> {categoryWizardState.slug || "(auto)"}
              </p>
              <p>
                <strong>Allowed steps:</strong> {categoryWizardState.allowedStepIds.join(", ")}
              </p>
              <p>
                <strong>Default steps:</strong> {categoryWizardState.defaultStepIds.join(", ")}
              </p>
              <p>
                <strong>Default fields:</strong> {categoryWizardState.defaultRequiredFieldsText}
              </p>
            </div>
          ) : null}
        </WizardModal>
      ) : null}
    </section>
  );
}
