import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import WizardModal from "../components/WizardModal.jsx";
import {
  archiveUseCase,
  createUseCase,
  getCategory,
  getUseCase,
  listCategories,
  listUseCases,
  publishUseCase,
  readableError,
  restoreUseCase,
  updateUseCaseDraft,
} from "../api.js";
import {
  STEP_LABELS,
  buildUseCasePayload,
  defaultUseCaseWizard,
  parseValidationError,
  useCaseWizardFromDetail,
} from "../utils/adminPayloads.js";

export default function ITAdminUseCasesPage() {
  const [categories, setCategories] = useState([]);
  const [useCases, setUseCases] = useState([]);
  const [categoryDetailsById, setCategoryDetailsById] = useState({});
  const [includeArchivedUseCases, setIncludeArchivedUseCases] = useState(false);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminError, setAdminError] = useState("");

  const [showUseCaseWizard, setShowUseCaseWizard] = useState(false);
  const [useCaseWizardMode, setUseCaseWizardMode] = useState("create");
  const [useCaseWizardStep, setUseCaseWizardStep] = useState(1);
  const [useCaseWizardBusy, setUseCaseWizardBusy] = useState(false);
  const [useCaseWizardError, setUseCaseWizardError] = useState("");
  const [useCaseWizardState, setUseCaseWizardState] = useState(null);

  const loadAdminData = async () => {
    setAdminLoading(true);
    setAdminError("");

    try {
      const [categoriesResponse, useCasesResponse] = await Promise.all([
        listCategories(true),
        listUseCases(includeArchivedUseCases),
      ]);
      setCategories(categoriesResponse.items);
      setUseCases(useCasesResponse.items);
    } catch (error) {
      setAdminError(readableError(error));
    } finally {
      setAdminLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, [includeArchivedUseCases]);

  const ensureCategoryDetail = async (categoryId) => {
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

  const openCreateUseCaseWizard = async () => {
    const availableCategories = categories.filter(
      (category) => !category.archived && category.published_version_number !== null,
    );

    if (availableCategories.length === 0) {
      setAdminError("No hay categorias publicadas. / Publish a category before creating use cases.");
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

  const openEditUseCaseWizard = async (useCaseId) => {
    setUseCaseWizardBusy(true);
    setUseCaseWizardError("");

    try {
      const response = await getUseCase(useCaseId);
      const wizard = useCaseWizardFromDetail(response.use_case);
      if (!wizard) {
        throw new Error("Use case has no draft or published definition.");
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

  const closeUseCaseWizard = () => {
    setShowUseCaseWizard(false);
    setUseCaseWizardState(null);
    setUseCaseWizardStep(1);
    setUseCaseWizardError("");
  };

  const setUseCaseField = (key, value) => {
    setUseCaseWizardState((prev) => ({ ...prev, [key]: value }));
  };

  const selectedUseCaseCategory = useCaseWizardState?.categoryId
    ? categoryDetailsById[useCaseWizardState.categoryId]
    : null;
  const selectedUseCaseAllowedSteps =
    selectedUseCaseCategory?.published_definition?.allowed_step_ids ?? [];

  const onUseCaseCategoryChange = async (categoryId) => {
    setUseCaseField("categoryId", categoryId);

    const detail = await ensureCategoryDetail(categoryId);
    const allowedStepIds = detail?.published_definition?.allowed_step_ids ?? [];

    setUseCaseWizardState((prev) => {
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

  const updateUseCaseStepAt = (index, updater) => {
    setUseCaseWizardState((prev) => {
      const nextSteps = [...prev.steps];
      nextSteps[index] = updater(nextSteps[index]);
      return { ...prev, steps: nextSteps };
    });
  };

  const addUseCaseStep = () => {
    const fallbackStep = selectedUseCaseAllowedSteps[0] ?? "manual_instruction";
    setUseCaseWizardState((prev) => ({
      ...prev,
      steps: [...prev.steps, { step_id: fallbackStep, params: {} }],
    }));
  };

  const removeUseCaseStep = (index) => {
    setUseCaseWizardState((prev) => ({
      ...prev,
      steps: prev.steps.filter((_, itemIndex) => itemIndex !== index),
    }));
  };

  const moveUseCaseStep = (index, direction) => {
    setUseCaseWizardState((prev) => {
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

  const validateUseCaseWizard = (wizardState) => {
    if (!wizardState.categoryId) {
      return "Selecciona categoria. / Select a category.";
    }
    if (!wizardState.displayName.trim()) {
      return "Nombre del caso obligatorio. / Display name is required.";
    }
    if (!wizardState.handoffDescription.trim()) {
      return "Handoff description is required.";
    }
    if (!wizardState.routingDescription.trim()) {
      return "Routing description is required.";
    }
    if (wizardState.steps.length === 0) {
      return "Define al menos un paso. / Add at least one step.";
    }
    return "";
  };

  const saveUseCaseDraft = async () => {
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
      setUseCaseWizardState((prev) => ({ ...prev, useCaseId: response.use_case.use_case_id }));
      await loadAdminData();
      return response.use_case;
    } catch (error) {
      setUseCaseWizardError(parseValidationError(readableError(error)));
      return null;
    } finally {
      setUseCaseWizardBusy(false);
    }
  };

  const publishUseCaseFromWizard = async () => {
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

  const publishUseCaseFromList = async (useCaseId) => {
    setAdminError("");
    try {
      await publishUseCase(useCaseId);
      await loadAdminData();
    } catch (error) {
      setAdminError(readableError(error));
    }
  };

  const archiveUseCaseFromList = async (useCaseId) => {
    setAdminError("");
    try {
      await archiveUseCase(useCaseId);
      await loadAdminData();
    } catch (error) {
      setAdminError(readableError(error));
    }
  };

  const restoreUseCaseFromList = async (useCaseId) => {
    setAdminError("");
    try {
      await restoreUseCase(useCaseId);
      await loadAdminData();
    } catch (error) {
      setAdminError(readableError(error));
    }
  };

  const manualUseCases = useCases.filter((item) => !item.is_system_default);
  const categoryDefaultUseCases = useCases.filter((item) => item.is_system_default);

  return (
    <section className="tab-panel admin-panel it-console-panel it-console-use-cases">
      <div className="admin-toolbar">
        <h2>Casos de uso / Use cases</h2>
        <div className="admin-toolbar-actions">
          <button type="button" className="ghost" onClick={loadAdminData} disabled={adminLoading}>
            Refresh
          </button>
          <button type="button" className="primary" onClick={openCreateUseCaseWizard}>
            Nuevo caso
          </button>
        </div>
      </div>

      <label className="toggle-row">
        <input
          type="checkbox"
          checked={includeArchivedUseCases}
          onChange={(event) => setIncludeArchivedUseCases(event.target.checked)}
        />
        <span>Mostrar archivados / Show archived</span>
      </label>
      <p className="helper">
        Category defines allowed workflow patterns. Use case defines the exact runnable step sequence.
      </p>
      <p className="helper">
        Manual use-cases are editable here. Category-generated defaults are read-only and sync from{" "}
        <Link to="/it/admin/categories">Categories</Link>.
      </p>

      {adminLoading ? <p className="helper">Cargando datos...</p> : null}
      {adminError ? <p className="error-text">{adminError}</p> : null}

      <div className="use-case-list">
        {manualUseCases.length === 0 ? (
          <div className="empty-state">No editable manual use-cases.</div>
        ) : (
          manualUseCases.map((item) => (
            <article key={item.use_case_id} className="use-case-card">
              <div>
                <h3>{item.display_name}</h3>
                <p className="helper">
                  slug: <code>{item.slug}</code> | category: <code>{item.category_id ?? "detached"}</code> |
                  category version: <code>{item.category_version_number ?? "-"}</code>
                </p>
                <div className="badge-row">
                  <span className={item.published_version_number ? "badge published" : "badge"}>
                    Published: {item.published_version_number ?? "-"}
                  </span>
                  <span className={item.draft_version_number ? "badge draft" : "badge"}>
                    Draft: {item.draft_version_number ?? "-"}
                  </span>
                  <span className={item.is_detached ? "badge detached" : "badge"}>
                    {item.is_detached ? "Detached" : "Linked"}
                  </span>
                  <span className={item.archived ? "badge archived" : "badge"}>
                    {item.archived ? "Archived" : "Active"}
                  </span>
                </div>
              </div>
              <div className="use-case-actions">
                <button
                  type="button"
                  className="ghost"
                  onClick={() => openEditUseCaseWizard(item.use_case_id)}
                >
                  Editar draft
                </button>
                <button
                  type="button"
                  className="primary"
                  disabled={!item.draft_version_number || item.archived}
                  onClick={() => publishUseCaseFromList(item.use_case_id)}
                >
                  Publicar
                </button>
                {item.archived ? (
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => restoreUseCaseFromList(item.use_case_id)}
                  >
                    Restaurar
                  </button>
                ) : (
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => archiveUseCaseFromList(item.use_case_id)}
                  >
                    Archivar
                  </button>
                )}
              </div>
            </article>
          ))
        )}
      </div>

      <div className="use-case-list">
        {categoryDefaultUseCases.length === 0 ? (
          <div className="empty-state">No category-generated defaults.</div>
        ) : (
          categoryDefaultUseCases.map((item) => (
            <article key={item.use_case_id} className="use-case-card">
              <div>
                <h3>{item.display_name}</h3>
                <p className="helper">
                  slug: <code>{item.slug}</code> | category: <code>{item.category_id ?? "detached"}</code> |
                  category version: <code>{item.category_version_number ?? "-"}</code>
                </p>
                <div className="badge-row">
                  <span className="badge default">Default / Predeterminado</span>
                  <span className={item.published_version_number ? "badge published" : "badge"}>
                    Published: {item.published_version_number ?? "-"}
                  </span>
                  <span className={item.draft_version_number ? "badge draft" : "badge"}>
                    Draft: {item.draft_version_number ?? "-"}
                  </span>
                  <span className={item.is_detached ? "badge detached" : "badge"}>
                    {item.is_detached ? "Detached" : "Linked"}
                  </span>
                  <span className={item.archived ? "badge archived" : "badge"}>
                    {item.archived ? "Archived" : "Active"}
                  </span>
                </div>
                <p className="helper">
                  Category-generated default (read-only here). Publish/archive/migrate via{" "}
                  <Link to="/it/admin/categories">Categories</Link>.
                </p>
              </div>
            </article>
          ))
        )}
      </div>

      {showUseCaseWizard && useCaseWizardState ? (
        <WizardModal
          title={useCaseWizardMode === "create" ? "Nuevo caso" : "Editar caso"}
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
                Anterior
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => setUseCaseWizardStep((prev) => Math.min(4, prev + 1))}
                disabled={useCaseWizardStep === 4}
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
                onClick={saveUseCaseDraft}
                disabled={useCaseWizardBusy}
              >
                Guardar draft
              </button>
              <button
                type="button"
                className="primary"
                onClick={publishUseCaseFromWizard}
                disabled={useCaseWizardBusy}
              >
                Guardar y publicar
              </button>
            </>
          }
        >
          {useCaseWizardStep === 1 ? (
            <div className="form-grid">
              <label>
                Categoria publicada
                <select
                  value={useCaseWizardState.categoryId}
                  onChange={(event) => onUseCaseCategoryChange(event.target.value)}
                >
                  <option value="">Select category</option>
                  {categories
                    .filter((category) => !category.archived && category.published_version_number !== null)
                    .map((category) => (
                      <option key={category.category_id} value={category.category_id}>
                        {category.display_name}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Nombre / Display name
                <input
                  value={useCaseWizardState.displayName}
                  onChange={(event) => setUseCaseField("displayName", event.target.value)}
                />
              </label>
              <label>
                Slug (optional)
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
                Handoff description
                <textarea
                  rows={3}
                  value={useCaseWizardState.handoffDescription}
                  onChange={(event) => setUseCaseField("handoffDescription", event.target.value)}
                />
              </label>
              <label>
                Routing description
                <textarea
                  rows={3}
                  value={useCaseWizardState.routingDescription}
                  onChange={(event) => setUseCaseField("routingDescription", event.target.value)}
                />
              </label>
              <label>
                Required fields (comma separated)
                <input
                  value={useCaseWizardState.requiredFieldsText}
                  onChange={(event) => setUseCaseField("requiredFieldsText", event.target.value)}
                />
              </label>
            </div>
          ) : null}

          {useCaseWizardStep === 3 ? (
            <div>
              <p className="helper">Pasos del flujo / Workflow steps.</p>
              <div className="step-list">
                {useCaseWizardState.steps.map((step, index) => (
                  <article key={`${step.step_id}-${index}`} className="step-item">
                    <label>
                      Step
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
                        {step.step_id === "append_resolution_note" ? "Note" : "Instruction"}
                        <input
                          value={
                            step.step_id === "append_resolution_note"
                              ? step.params.note ?? ""
                              : step.params.instruction ?? ""
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
                      <button type="button" className="ghost" onClick={() => moveUseCaseStep(index, -1)}>
                        Up
                      </button>
                      <button type="button" className="ghost" onClick={() => moveUseCaseStep(index, 1)}>
                        Down
                      </button>
                      <button type="button" className="ghost" onClick={() => removeUseCaseStep(index)}>
                        Remove
                      </button>
                    </div>
                  </article>
                ))}
              </div>
              <button type="button" className="ghost" onClick={addUseCaseStep}>
                Agregar paso / Add step
              </button>
            </div>
          ) : null}

          {useCaseWizardStep === 4 ? (
            <div className="review-box">
              <h4>Review</h4>
              <p>
                <strong>Display:</strong> {useCaseWizardState.displayName}
              </p>
              <p>
                <strong>Category:</strong> {useCaseWizardState.categoryId || "none"}
              </p>
              <p>
                <strong>Required fields:</strong> {useCaseWizardState.requiredFieldsText}
              </p>
              <p>
                <strong>Steps:</strong> {useCaseWizardState.steps.map((step) => step.step_id).join(" -> ")}
              </p>
            </div>
          ) : null}
        </WizardModal>
      ) : null}
    </section>
  );
}
