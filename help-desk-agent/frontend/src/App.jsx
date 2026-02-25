import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";

import {
  adminAssistantChat,
  archiveCategory,
  archiveUseCase,
  chatStream,
  createCategory,
  createUseCase,
  getCategory,
  getUseCase,
  listCategories,
  listSteps,
  listUseCases,
  migrateUseCaseCategoryVersion,
  publishCategory,
  publishUseCase,
  readableError,
  resetAdminAssistantConversation,
  resetConversation,
  restoreCategory,
  restoreUseCase,
  updateCategoryDraft,
  updateUseCaseDraft,
} from "./api.js";

const SAMPLE_PROMPTS = [
  {
    label: "Reset acceso",
    text: [
      "Reset de acceso Ecrew:",
      "https://volotea.atlassian.net/browse/USDV-176285 - Francois Emeriau- Log in problem into eCrew",
      "Tipo de actividad: Service request",
      "Portal Group: Login ans accounts",
      "Tipo de sol: Fix an account issue",
    ].join("\n"),
  },
  {
    label: "Onboarding alta",
    text: [
      "https://volotea.atlassian.net/browse/USDV-176893 - ALTAS E-MAIL/EFOS/PELESYS 16-02-2026",
      "Tipo de actividad: Service request",
      "Portal group: Login ans accounts",
      "Tipo de sol: Onboard new employee",
    ].join("\n"),
  },
];

const STEP_LABELS = {
  verify_requester: "Verificar solicitante / Verify requester",
  reset_ecrew_access: "Reset eCrew access",
  provision_email: "Provision E-MAIL",
  provision_efos: "Provision EFOS",
  provision_pelesys: "Provision PELESYS",
  append_resolution_note: "Append resolution note",
  manual_instruction: "Manual instruction",
};

const MARKDOWN_PLUGINS = [remarkGfm, remarkBreaks];

function nextIdFactory() {
  let count = 0;
  return () => {
    count += 1;
    return `entry-${count}`;
  };
}

function parseCsv(rawValue) {
  return rawValue
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinCsv(values) {
  return values.join(", ");
}

function defaultCategoryWizard(stepCatalog) {
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

function categoryWizardFromDetail(detail) {
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

function defaultUseCaseWizard(categoryId, allowedStepIds) {
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

function useCaseWizardFromDetail(detail) {
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

function buildCategoryPayload(wizardState) {
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

function buildUseCasePayload(wizardState) {
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

function parseValidationError(errorMessage) {
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

function normalizeEntryKind(value) {
  if (typeof value !== "string" || value.trim() === "") {
    return "info";
  }
  return value;
}

function normalizeEntryText(value) {
  if (typeof value === "string") {
    return value;
  }
  if (value === null || value === undefined) {
    return "";
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function renderEvents(entries, isThinking = false, thinkingAgent = "Assistant") {
  const renderedEntries = entries.map((entry) => {
    const kind = normalizeEntryKind(entry.kind);
    const text = normalizeEntryText(entry.text);
    const roleClass = typeof entry.role === "string" ? entry.role : "assistant";
    return (
      <article
        key={entry.id}
        className={`entry entry-${roleClass} kind-${kind.replace("_", "-")}`}
      >
        <div className="meta">
          {entry.agent} <span>{kind}</span>
        </div>
        <div className="entry-markdown">
          <ReactMarkdown
            remarkPlugins={MARKDOWN_PLUGINS}
            components={{
              a: ({ node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
            }}
          >
            {text}
          </ReactMarkdown>
        </div>
      </article>
    );
  });

  if (isThinking) {
    renderedEntries.push(
      <article key={`thinking-${thinkingAgent}`} className="entry entry-assistant kind-thinking">
        <div className="meta">
          {thinkingAgent} <span>thinking</span>
        </div>
        <div className="thinking-dots" aria-label="Model is thinking">
          <span>.</span>
          <span>.</span>
          <span>.</span>
        </div>
      </article>,
    );
  }

  if (renderedEntries.length === 0) {
    return (
      <div className="empty-state">Pega un ticket y empieza. / Paste a ticket to start.</div>
    );
  }

  return renderedEntries;
}

export default function App() {
  const nextId = useMemo(() => nextIdFactory(), []);

  const transcriptRef = useRef(null);
  const techTranscriptRef = useRef(null);

  const [activeTab, setActiveTab] = useState("chat");
  const [adminSection, setAdminSection] = useState("categories");

  const [chatInput, setChatInput] = useState("");
  const [entries, setEntries] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [currentAgent, setCurrentAgent] = useState("Help Desk Triage Agent");
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState("");

  const [techInput, setTechInput] = useState("");
  const [techEntries, setTechEntries] = useState([]);
  const [techConversationId, setTechConversationId] = useState(null);
  const [techCurrentAgent, setTechCurrentAgent] = useState("Tech Team Assistant Triage");
  const [techSending, setTechSending] = useState(false);
  const [techError, setTechError] = useState("");

  const [steps, setSteps] = useState([]);
  const [categories, setCategories] = useState([]);
  const [useCases, setUseCases] = useState([]);
  const [categoryDetailsById, setCategoryDetailsById] = useState({});
  const [includeArchivedCategories, setIncludeArchivedCategories] = useState(false);
  const [includeArchivedUseCases, setIncludeArchivedUseCases] = useState(false);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminError, setAdminError] = useState("");
  const [categoryPublishNotice, setCategoryPublishNotice] = useState("");

  const [showCategoryWizard, setShowCategoryWizard] = useState(false);
  const [categoryWizardMode, setCategoryWizardMode] = useState("create");
  const [categoryWizardStep, setCategoryWizardStep] = useState(1);
  const [categoryWizardBusy, setCategoryWizardBusy] = useState(false);
  const [categoryWizardError, setCategoryWizardError] = useState("");
  const [categoryWizardState, setCategoryWizardState] = useState(null);

  const [showUseCaseWizard, setShowUseCaseWizard] = useState(false);
  const [useCaseWizardMode, setUseCaseWizardMode] = useState("create");
  const [useCaseWizardStep, setUseCaseWizardStep] = useState(1);
  const [useCaseWizardBusy, setUseCaseWizardBusy] = useState(false);
  const [useCaseWizardError, setUseCaseWizardError] = useState("");
  const [useCaseWizardState, setUseCaseWizardState] = useState(null);

  const [migrationPrompt, setMigrationPrompt] = useState(null);

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [entries, isSending]);

  useEffect(() => {
    if (techTranscriptRef.current) {
      techTranscriptRef.current.scrollTop = techTranscriptRef.current.scrollHeight;
    }
  }, [techEntries, techSending]);

  const loadAdminData = async () => {
    setAdminLoading(true);
    setAdminError("");
    try {
      const [stepsResponse, categoriesResponse, useCasesResponse] = await Promise.all([
        listSteps(),
        listCategories(includeArchivedCategories),
        listUseCases(includeArchivedUseCases),
      ]);
      setSteps(stepsResponse.items);
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
  }, [includeArchivedCategories, includeArchivedUseCases]);

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

  const sendMessage = async (messageText) => {
    const userEntry = {
      id: nextId(),
      role: "user",
      kind: "user",
      agent: "You",
      text: messageText,
    };
    const streamingEntryId = nextId();
    const streamingEntry = {
      id: streamingEntryId,
      role: "assistant",
      kind: "message",
      agent: currentAgent,
      text: "",
    };

    setEntries((prev) => [...prev, userEntry, streamingEntry]);
    setChatError("");
    setIsSending(true);
    let hasStreamedText = false;

    try {
      const finalPayload = await chatStream(messageText, conversationId, (streamEvent) => {
        if (!streamEvent || typeof streamEvent !== "object") {
          return;
        }

        if (streamEvent.type === "start") {
          if (streamEvent.conversation_id) {
            setConversationId(streamEvent.conversation_id);
          }
          if (streamEvent.current_agent) {
            setCurrentAgent(streamEvent.current_agent);
          }
          return;
        }

        if (streamEvent.type === "agent_updated") {
          if (streamEvent.agent) {
            setCurrentAgent(streamEvent.agent);
          }
          return;
        }

        if (streamEvent.type === "text_delta") {
          const delta = typeof streamEvent.delta === "string" ? streamEvent.delta : "";
          if (!delta) {
            return;
          }
          hasStreamedText = true;
          setEntries((prev) =>
            prev.map((entry) =>
              entry.id === streamingEntryId ? { ...entry, text: `${entry.text}${delta}` } : entry,
            ),
          );
          return;
        }

        if (streamEvent.type === "event") {
          const event = streamEvent.event;
          if (!event || typeof event !== "object") {
            return;
          }

          if (event.kind === "message") {
            const messageTextEvent = typeof event.text === "string" ? event.text : "";
            if (!hasStreamedText && messageTextEvent) {
              hasStreamedText = true;
              setEntries((prev) =>
                prev.map((entry) =>
                  entry.id === streamingEntryId
                    ? {
                        ...entry,
                        agent: event.agent ?? entry.agent,
                        kind: event.kind ?? entry.kind,
                        text: messageTextEvent,
                      }
                    : entry,
                ),
              );
            }
            return;
          }

          setEntries((prev) => [
            ...prev,
            {
              id: nextId(),
              role: "assistant",
              kind: event.kind ?? "info",
              agent: event.agent ?? "Assistant",
              text: event.text ?? "",
            },
          ]);
        }
      });

      if (finalPayload?.conversation_id) {
        setConversationId(finalPayload.conversation_id);
      }
      if (finalPayload?.current_agent) {
        setCurrentAgent(finalPayload.current_agent);
      }
      if (!hasStreamedText) {
        setEntries((prev) => prev.filter((entry) => entry.id !== streamingEntryId));
      }
    } catch (error) {
      setEntries((prev) => prev.filter((entry) => entry.id !== streamingEntryId));
      setChatError(readableError(error));
    } finally {
      setIsSending(false);
    }
  };

  const sendTechMessage = async (messageText) => {
    const userEntry = {
      id: nextId(),
      role: "user",
      kind: "user",
      agent: "Tech Team",
      text: messageText,
    };
    setTechEntries((prev) => [...prev, userEntry]);
    setTechError("");
    setTechSending(true);

    try {
      const data = await adminAssistantChat(messageText, techConversationId);
      setTechConversationId(data.conversation_id);
      setTechCurrentAgent(data.current_agent);
      const agentEntries = data.events.map((event) => ({
        id: nextId(),
        role: "assistant",
        kind: event.kind,
        agent: event.agent,
        text: event.text,
      }));
      setTechEntries((prev) => [...prev, ...agentEntries]);
    } catch (error) {
      setTechError(readableError(error));
    } finally {
      setTechSending(false);
    }
  };

  const handleChatSubmit = async (event) => {
    event.preventDefault();
    const messageText = chatInput.trim();
    if (!messageText || isSending) {
      return;
    }
    setChatInput("");
    await sendMessage(messageText);
  };

  const handleTechSubmit = async (event) => {
    event.preventDefault();
    const messageText = techInput.trim();
    if (!messageText || techSending) {
      return;
    }
    setTechInput("");
    await sendTechMessage(messageText);
  };

  const handleCtrlEnterSubmit = (event) => {
    if (event.key === "Enter" && event.ctrlKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  const handleChatReset = async () => {
    if (conversationId) {
      try {
        await resetConversation(conversationId);
      } catch (error) {
        setChatError(readableError(error));
      }
    }
    setEntries([]);
    setConversationId(null);
    setCurrentAgent("Help Desk Triage Agent");
    setChatInput("");
  };

  const handleTechReset = async () => {
    if (techConversationId) {
      try {
        await resetAdminAssistantConversation(techConversationId);
      } catch (error) {
        setTechError(readableError(error));
      }
    }
    setTechEntries([]);
    setTechConversationId(null);
    setTechCurrentAgent("Tech Team Assistant Triage");
    setTechInput("");
  };

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

  const publishCategoryFromWizard = async () => {
    const saved = await saveCategoryDraft();
    if (!saved) {
      return;
    }
    await publishCategoryAndPromptMigration(saved.category_id);
    closeCategoryWizard();
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

  const openCreateUseCaseWizard = async () => {
    const availableCategories = categories.filter(
      (category) => !category.archived && category.published_version_number !== null,
    );

    if (availableCategories.length === 0) {
      setAdminError(
        "No hay categorias publicadas. / Publish a category before creating use cases.",
      );
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

  return (
    <div className="app-shell">
      <header className="header">
        <h1>Help Desk Agent Builder</h1>
        <p>Soporte no tecnico: chat operativo, categorias y asistente tecnico agentico.</p>
      </header>

      <nav className="tab-row">
        <button
          type="button"
          className={activeTab === "chat" ? "tab active" : "tab"}
          onClick={() => setActiveTab("chat")}
        >
          Chat
        </button>
        <button
          type="button"
          className={activeTab === "admin" ? "tab active" : "tab"}
          onClick={() => setActiveTab("admin")}
        >
          Admin
        </button>
        <button
          type="button"
          className={activeTab === "tech" ? "tab active" : "tab"}
          onClick={() => setActiveTab("tech")}
        >
          Tech Assistant
        </button>
      </nav>

      {activeTab === "chat" ? (
        <section className="tab-panel chat-panel">
          <section className="status-row">
            <div>
              <span className="label">Conversation</span>
              <strong>{conversationId ?? "new"}</strong>
            </div>
            <div>
              <span className="label">Current agent</span>
              <strong>{currentAgent}</strong>
            </div>
          </section>

          <section className="sample-row">
            {SAMPLE_PROMPTS.map((prompt) => (
              <button
                key={prompt.label}
                type="button"
                className="sample-button"
                onClick={() => setChatInput(prompt.text)}
              >
                {prompt.label}
              </button>
            ))}
          </section>

          <section className="transcript" ref={transcriptRef}>
            {renderEvents(entries, isSending, currentAgent)}
          </section>

          <form className="composer" onSubmit={handleChatSubmit}>
            <textarea
              value={chatInput}
              onChange={(event) => setChatInput(event.target.value)}
              onKeyDown={handleCtrlEnterSubmit}
              placeholder="Describe el ticket... / Describe the ticket..."
              rows={4}
              disabled={isSending}
            />
            <div className="composer-actions">
              <button type="button" className="ghost" onClick={handleChatReset} disabled={isSending}>
                Nuevo chat
              </button>
              <button type="submit" className="primary" disabled={isSending}>
                {isSending ? "Enviando..." : "Enviar"}
              </button>
            </div>
          </form>

          {chatError ? <aside className="error-banner">{chatError}</aside> : null}
        </section>
      ) : null}

      {activeTab === "tech" ? (
        <section className="tab-panel tech-panel">
          <section className="status-row">
            <div>
              <span className="label">Tech Session</span>
              <strong>{techConversationId ?? "new"}</strong>
            </div>
            <div>
              <span className="label">Current agent</span>
              <strong>{techCurrentAgent}</strong>
            </div>
          </section>

          <section className="transcript" ref={techTranscriptRef}>
            {renderEvents(techEntries, techSending, techCurrentAgent)}
          </section>

          <form className="composer" onSubmit={handleTechSubmit}>
            <textarea
              value={techInput}
              onChange={(event) => setTechInput(event.target.value)}
              onKeyDown={handleCtrlEnterSubmit}
              placeholder="Pide ayuda para crear categorias... / Ask how to create categories..."
              rows={4}
              disabled={techSending}
            />
            <div className="composer-actions">
              <button type="button" className="ghost" onClick={handleTechReset} disabled={techSending}>
                Nueva sesion
              </button>
              <button type="submit" className="primary" disabled={techSending}>
                {techSending ? "Enviando..." : "Enviar"}
              </button>
            </div>
          </form>

          {techError ? <aside className="error-banner">{techError}</aside> : null}
        </section>
      ) : null}

      {activeTab === "admin" ? (
        <section className="tab-panel admin-panel">
          <div className="sub-tab-row">
            <button
              type="button"
              className={adminSection === "categories" ? "tab active" : "tab"}
              onClick={() => setAdminSection("categories")}
            >
              Categorias
            </button>
            <button
              type="button"
              className={adminSection === "usecases" ? "tab active" : "tab"}
              onClick={() => setAdminSection("usecases")}
            >
              Casos de uso
            </button>
          </div>

          <div className="admin-toolbar">
            <h2>
              {adminSection === "categories"
                ? "Categorias / Categories"
                : "Casos de uso / Use cases"}
            </h2>
            <div className="admin-toolbar-actions">
              <button type="button" className="ghost" onClick={loadAdminData} disabled={adminLoading}>
                Refresh
              </button>
              {adminSection === "categories" ? (
                <button type="button" className="primary" onClick={openCreateCategoryWizard}>
                  Nueva categoria
                </button>
              ) : (
                <button type="button" className="primary" onClick={openCreateUseCaseWizard}>
                  Nuevo caso
                </button>
              )}
            </div>
          </div>

          {adminSection === "categories" ? (
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={includeArchivedCategories}
                onChange={(event) => setIncludeArchivedCategories(event.target.checked)}
              />
              <span>Mostrar archivadas / Show archived</span>
            </label>
          ) : (
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={includeArchivedUseCases}
                onChange={(event) => setIncludeArchivedUseCases(event.target.checked)}
              />
              <span>Mostrar archivados / Show archived</span>
            </label>
          )}

          {adminLoading ? <p className="helper">Cargando datos...</p> : null}
          {adminError ? <p className="error-text">{adminError}</p> : null}
          {categoryPublishNotice ? <p className="helper">{categoryPublishNotice}</p> : null}

          {migrationPrompt ? (
            <section className="migration-box">
              <h3>Migracion sugerida / Suggested migration</h3>
              <p>
                Categoria publicada con version <strong>{migrationPrompt.categoryVersionNumber}</strong>.
                Selecciona los casos a migrar.
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

          {adminSection === "categories" ? (
            <div className="use-case-list">
              {categories.length === 0 ? (
                <div className="empty-state">No hay categorias.</div>
              ) : (
                categories.map((item) => (
                  <article key={item.category_id} className="use-case-card">
                    <div>
                      <h3>{item.display_name}</h3>
                      <p className="helper">
                        id: <code>{item.category_id}</code> | slug: <code>{item.slug}</code>
                      </p>
                      <div className="badge-row">
                        <span className={item.published_version_number ? "badge published" : "badge"}>
                          Published: {item.published_version_number ?? "-"}
                        </span>
                        <span className={item.draft_version_number ? "badge draft" : "badge"}>
                          Draft: {item.draft_version_number ?? "-"}
                        </span>
                        <span className={item.archived ? "badge archived" : "badge"}>
                          {item.archived ? "Archived" : "Active"}
                        </span>
                      </div>
                    </div>
                    <div className="use-case-actions">
                      <button type="button" className="ghost" onClick={() => openEditCategoryWizard(item.category_id)}>
                        Editar draft
                      </button>
                      <button
                        type="button"
                        className="primary"
                        disabled={!item.draft_version_number || item.archived}
                        onClick={() => publishCategoryAndPromptMigration(item.category_id)}
                      >
                        Publicar
                      </button>
                      {item.archived ? (
                        <button
                          type="button"
                          className="ghost"
                          onClick={() => restoreCategoryFromList(item.category_id)}
                        >
                          Restaurar
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="ghost"
                          onClick={() => archiveCategoryFromList(item.category_id)}
                        >
                          Archivar
                        </button>
                      )}
                    </div>
                  </article>
                ))
              )}
            </div>
          ) : (
            <div className="use-case-list">
              {useCases.length === 0 ? (
                <div className="empty-state">No hay casos de uso.</div>
              ) : (
                useCases.map((item) => (
                  <article key={item.use_case_id} className="use-case-card">
                    <div>
                      <h3>{item.display_name}</h3>
                      <p className="helper">
                        slug: <code>{item.slug}</code> | category: <code>{item.category_id ?? "detached"}</code> |
                        category version: <code>{item.category_version_number ?? "-"}</code>
                      </p>
                      <div className="badge-row">
                        {item.is_system_default ? <span className="badge default">Default / Predeterminado</span> : null}
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
                      {item.is_system_default ? (
                        <p className="helper">
                          This use-case is generated from category defaults and auto-syncs on category publish.
                        </p>
                      ) : null}
                    </div>
                    <div className="use-case-actions">
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => openEditUseCaseWizard(item.use_case_id)}
                        disabled={item.is_system_default}
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
                          disabled={item.is_system_default}
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
          )}

          {showCategoryWizard && categoryWizardState ? (
            <section className="wizard-shell">
              <header className="wizard-header">
                <h3>
                  {categoryWizardMode === "create" ? "Nueva categoria" : "Editar categoria"} - Paso {categoryWizardStep}/4
                </h3>
                <button type="button" className="ghost" onClick={closeCategoryWizard}>
                  Cerrar
                </button>
              </header>

              <div className="wizard-body">
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
                        onChange={(event) =>
                          setCategoryField("defaultHandoffDescription", event.target.value)
                        }
                      />
                    </label>
                    <label>
                      Routing description
                      <textarea
                        rows={3}
                        value={categoryWizardState.defaultRoutingDescription}
                        onChange={(event) =>
                          setCategoryField("defaultRoutingDescription", event.target.value)
                        }
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
              </div>

              <footer className="wizard-footer">
                <div className="wizard-nav">
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
                </div>
                <div className="wizard-submit">
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
                </div>
              </footer>

              {categoryWizardError ? <p className="error-text">{categoryWizardError}</p> : null}
            </section>
          ) : null}

          {showUseCaseWizard && useCaseWizardState ? (
            <section className="wizard-shell">
              <header className="wizard-header">
                <h3>
                  {useCaseWizardMode === "create" ? "Nuevo caso" : "Editar caso"} - Paso {useCaseWizardStep}/4
                </h3>
                <button type="button" className="ghost" onClick={closeUseCaseWizard}>
                  Cerrar
                </button>
              </header>

              <div className="wizard-body">
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
                          .filter(
                            (category) =>
                              !category.archived && category.published_version_number !== null,
                          )
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
              </div>

              <footer className="wizard-footer">
                <div className="wizard-nav">
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
                </div>
                <div className="wizard-submit">
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
                </div>
              </footer>

              {useCaseWizardError ? <p className="error-text">{useCaseWizardError}</p> : null}
            </section>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
