import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import Breadcrumb from "../components/Breadcrumb";
import { useI18n } from "../i18n/useI18n";
import { getTicket, listTickets, readableError } from "../api";

function formatTimestamp(value, language) {
  if (!value) {
    return language === "es" ? "-" : "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(language === "es" ? "es-ES" : "en-US");
}

function prettyPayload(raw) {
  if (typeof raw !== "string" || raw.trim() === "") {
    return "";
  }
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

export default function ITAdminTicketsPage() {
  const { language, t } = useI18n();
  const [searchParams] = useSearchParams();
  const filterUseCaseId = searchParams.get("use_case_id") || "";

  const [statusFilter, setStatusFilter] = useState("");
  const [conversationFilter, setConversationFilter] = useState("");
  const [externalTicketFilter, setExternalTicketFilter] = useState("");

  const [tickets, setTickets] = useState([]);
  const [selectedTicketId, setSelectedTicketId] = useState(null);
  const [selectedTicket, setSelectedTicket] = useState(null);

  const [listLoading, setListLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const statusOptions = [
    { value: "", label: t("ticketPage.statusAll") },
    { value: "open", label: t("common.statusOpen") },
    { value: "in_progress", label: t("common.statusInProgress") },
    { value: "resolved", label: t("common.statusResolved") },
  ];

  const statusLabel = (value) => {
    if (value === "open") {
      return t("common.statusOpen");
    }
    if (value === "in_progress") {
      return t("common.statusInProgress");
    }
    if (value === "resolved") {
      return t("common.statusResolved");
    }
    return value;
  };

  const loadTickets = async () => {
    setListLoading(true);
    setErrorMessage("");
    try {
      const response = await listTickets({
        status: statusFilter || undefined,
        conversationId: conversationFilter.trim() || undefined,
        externalTicketId: externalTicketFilter.trim() || undefined,
        useCaseId: filterUseCaseId || undefined,
        limit: 100,
        offset: 0,
      });
      setTickets(response.items);
      if (response.items.length === 0) {
        setSelectedTicketId(null);
        setSelectedTicket(null);
      } else if (!selectedTicketId || !response.items.some((item) => item.ticket_id === selectedTicketId)) {
        setSelectedTicketId(response.items[0].ticket_id);
      }
    } catch (error) {
      setErrorMessage(readableError(error));
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    loadTickets();
    // Reload when URL use_case_id param changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterUseCaseId]);

  useEffect(() => {
    if (!selectedTicketId) {
      setSelectedTicket(null);
      return;
    }

    let isCancelled = false;
    const loadDetail = async () => {
      setDetailLoading(true);
      setErrorMessage("");
      try {
        const response = await getTicket(selectedTicketId);
        if (!isCancelled) {
          setSelectedTicket(response.ticket);
        }
      } catch (error) {
        if (!isCancelled) {
          setErrorMessage(readableError(error));
          setSelectedTicket(null);
        }
      } finally {
        if (!isCancelled) {
          setDetailLoading(false);
        }
      }
    };

    loadDetail();
    return () => {
      isCancelled = true;
    };
  }, [selectedTicketId]);

  const handleFilterSubmit = async (event) => {
    event.preventDefault();
    await loadTickets();
  };

  return (
    <section className="tab-panel admin-panel it-console-panel it-console-tickets">
      <Breadcrumb
        items={[
          { label: t("common.dashboard"), to: "/it/dashboard" },
          ...(filterUseCaseId
            ? [{ label: filterUseCaseId.slice(0, 20), to: "/it/admin/use-cases" }]
            : []),
          { label: t("common.tickets") },
        ]}
      />
      <div className="admin-toolbar">
        <h2>{t("ticketPage.title")}</h2>
        <div className="admin-toolbar-actions">
          <button type="button" className="ghost" onClick={loadTickets} disabled={listLoading}>
            {t("common.refresh")}
          </button>
        </div>
      </div>

      <form className="ticket-filter-row" onSubmit={handleFilterSubmit}>
        <label>
          {t("ticketPage.filterStatus")}
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            {statusOptions.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("ticketPage.filterConversation")}
          <input
            type="text"
            value={conversationFilter}
            onChange={(event) => setConversationFilter(event.target.value)}
            placeholder={t("ticketPage.filterConversationPlaceholder")}
          />
        </label>
        <label>
          {t("ticketPage.filterExternalTicket")}
          <input
            type="text"
            value={externalTicketFilter}
            onChange={(event) => setExternalTicketFilter(event.target.value)}
            placeholder="USDV-176285"
          />
        </label>
        <button type="submit" className="primary" disabled={listLoading}>
          {t("common.applyFilters")}
        </button>
      </form>

      {listLoading ? <p className="helper">{t("ticketPage.loadingRegistry")}</p> : null}
      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

      <div className="ticket-registry-layout">
        <aside className="ticket-list-pane">
          {tickets.length === 0 ? (
            <p className="helper">{t("ticketPage.emptyList")}</p>
          ) : (
            <div className="ticket-list">
              {tickets.map((item) => (
                <button
                  key={item.ticket_id}
                  type="button"
                  className={`ticket-list-item ${selectedTicketId === item.ticket_id ? "selected" : ""}`}
                  onClick={() => setSelectedTicketId(item.ticket_id)}
                >
                  <strong>{item.external_ticket_id || item.ticket_id.slice(0, 12)}</strong>
                  <span>{item.use_case_display_name || item.use_case_id}</span>
                  <span className={`badge ${item.status}`}>{statusLabel(item.status)}</span>
                  <span className="helper">{formatTimestamp(item.created_at, language)}</span>
                </button>
              ))}
            </div>
          )}
        </aside>

        <section className="ticket-detail-pane">
          {detailLoading ? <p className="helper">{t("ticketPage.loadingDetail")}</p> : null}
          {!detailLoading && !selectedTicket ? (
            <p className="helper">{t("ticketPage.selectTicket")}</p>
          ) : null}
          {!detailLoading && selectedTicket ? (
            <article className="ticket-detail-card">
              <div className="ticket-detail-header">
                <h3>{selectedTicket.external_ticket_id || selectedTicket.ticket_id}</h3>
                <span className={`badge ${selectedTicket.status}`}>{statusLabel(selectedTicket.status)}</span>
              </div>
              <div className="ticket-detail-meta">
                <span>{t("common.fieldRunbook")}: <strong>{selectedTicket.use_case_display_name || selectedTicket.use_case_id}</strong></span>
                <span>{t("common.fieldConversation")}: <code>{selectedTicket.conversation_id || t("common.notAvailable")}</code></span>
                <span>{t("common.fieldCreated")}: {formatTimestamp(selectedTicket.created_at, language)}</span>
                {selectedTicket.resolved_at ? (
                  <span>{t("common.fieldResolved")}: {formatTimestamp(selectedTicket.resolved_at, language)}</span>
                ) : null}
              </div>
              {selectedTicket.error_message ? (
                <p className="error-text">
                  {t("common.fieldError")}: <code>{selectedTicket.error_message}</code>
                </p>
              ) : null}

              <div className="ticket-context-box">
                <h4>{t("ticketPage.detailContext")}</h4>
                <pre>{selectedTicket.ticket_context}</pre>
              </div>

              <div className="ticket-detail-grid">
                <div className="ticket-detail-cell">
                  <h4>{t("ticketPage.detailStatusHistory")}</h4>
                  <div className="ticket-table">
                    {selectedTicket.status_history.length === 0 ? (
                      <p className="helper">{t("ticketPage.noStatusHistory")}</p>
                    ) : selectedTicket.status_history.map((item, index) => (
                      <div key={`${item.status}-${item.changed_at}-${index}`} className="ticket-table-row">
                        <span className={`badge ${item.status}`}>{statusLabel(item.status)}</span>
                        <span>{formatTimestamp(item.changed_at, language)}</span>
                        <span>{item.reason || t("common.notAvailable")}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="ticket-detail-cell">
                  <h4>{t("ticketPage.detailExtractedFields")}</h4>
                  <div className="ticket-table">
                    {selectedTicket.fields.length === 0 ? (
                      <p className="helper">{t("ticketPage.noFields")}</p>
                    ) : selectedTicket.fields.map((item, index) => (
                      <div key={`${item.field_name}-${index}`} className="ticket-table-row">
                        <span><strong>{item.field_name}</strong></span>
                        <span>{item.field_value}</span>
                        <span>
                          {item.source}
                          {item.is_required ? ` ${t("common.requiredSuffix")}` : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="ticket-detail-cell">
                  <h4>{t("ticketPage.detailWorkflowSteps")}</h4>
                  <div className="ticket-table">
                    {selectedTicket.steps.length === 0 ? (
                      <p className="helper">{t("ticketPage.noSteps")}</p>
                    ) : selectedTicket.steps.map((item, index) => (
                      <div key={`${item.step_order}-${index}`} className="ticket-table-row">
                        <span className="badge">{item.step_order}</span>
                        <span><strong>{item.step_id}</strong></span>
                        <span>{item.output_text}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="ticket-detail-cell">
                  <h4>{t("ticketPage.detailEvents")}</h4>
                  <div className="ticket-table">
                    {selectedTicket.events.length === 0 ? (
                      <p className="helper">{t("ticketPage.noEvents")}</p>
                    ) : selectedTicket.events.map((item, index) => (
                      <div key={`${item.event_type}-${item.created_at}-${index}`} className="ticket-table-row">
                        <span><strong>{item.event_type}</strong></span>
                        <span>{item.agent_name || t("common.notAvailable")}</span>
                        <span>
                          <pre>{prettyPayload(item.payload_json)}</pre>
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </article>
          ) : null}
        </section>
      </div>
    </section>
  );
}
