import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import Breadcrumb from "../components/Breadcrumb.jsx";
import { getTicket, listTickets, readableError } from "../api.js";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "open", label: "open" },
  { value: "in_progress", label: "in_progress" },
  { value: "resolved", label: "resolved" },
];

function formatTimestamp(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
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
          { label: "Dashboard", to: "/it/dashboard" },
          ...(filterUseCaseId
            ? [{ label: filterUseCaseId.slice(0, 20), to: "/it/admin/use-cases" }]
            : []),
          { label: "Tickets" },
        ]}
      />
      <div className="admin-toolbar">
        <h2>Tickets</h2>
        <div className="admin-toolbar-actions">
          <button type="button" className="ghost" onClick={loadTickets} disabled={listLoading}>
            Refresh
          </button>
        </div>
      </div>

      <form className="ticket-filter-row" onSubmit={handleFilterSubmit}>
        <label>
          Status
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Conversation
          <input
            type="text"
            value={conversationFilter}
            onChange={(event) => setConversationFilter(event.target.value)}
            placeholder="conversation_id"
          />
        </label>
        <label>
          External ticket
          <input
            type="text"
            value={externalTicketFilter}
            onChange={(event) => setExternalTicketFilter(event.target.value)}
            placeholder="USDV-176285"
          />
        </label>
        <button type="submit" className="primary" disabled={listLoading}>
          Apply filters
        </button>
      </form>

      {listLoading ? <p className="helper">Loading ticket registry...</p> : null}
      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

      <div className="ticket-registry-layout">
        <aside className="ticket-list-pane">
          {tickets.length === 0 ? (
            <p className="helper">No tickets found for the selected filters.</p>
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
                  <span className={`badge ${item.status}`}>{item.status}</span>
                  <span className="helper">{formatTimestamp(item.created_at)}</span>
                </button>
              ))}
            </div>
          )}
        </aside>

        <section className="ticket-detail-pane">
          {detailLoading ? <p className="helper">Loading ticket detail...</p> : null}
          {!detailLoading && !selectedTicket ? (
            <p className="helper">Select a ticket to inspect structured execution details.</p>
          ) : null}
          {!detailLoading && selectedTicket ? (
            <article className="ticket-detail-card">
              <div className="ticket-detail-header">
                <h3>{selectedTicket.external_ticket_id || selectedTicket.ticket_id}</h3>
                <span className={`badge ${selectedTicket.status}`}>{selectedTicket.status}</span>
              </div>
              <div className="ticket-detail-meta">
                <span>Runbook: <strong>{selectedTicket.use_case_display_name || selectedTicket.use_case_id}</strong></span>
                <span>Conversation: <code>{selectedTicket.conversation_id || "-"}</code></span>
                <span>Created: {formatTimestamp(selectedTicket.created_at)}</span>
                {selectedTicket.resolved_at ? (
                  <span>Resolved: {formatTimestamp(selectedTicket.resolved_at)}</span>
                ) : null}
              </div>
              {selectedTicket.error_message ? (
                <p className="error-text">
                  Error: <code>{selectedTicket.error_message}</code>
                </p>
              ) : null}

              <div className="ticket-context-box">
                <h4>Ticket context</h4>
                <pre>{selectedTicket.ticket_context}</pre>
              </div>

              <div className="ticket-detail-grid">
                <div className="ticket-detail-cell">
                  <h4>Status history</h4>
                  <div className="ticket-table">
                    {selectedTicket.status_history.length === 0 ? (
                      <p className="helper">No status changes yet.</p>
                    ) : selectedTicket.status_history.map((item, index) => (
                      <div key={`${item.status}-${item.changed_at}-${index}`} className="ticket-table-row">
                        <span className={`badge ${item.status}`}>{item.status}</span>
                        <span>{formatTimestamp(item.changed_at)}</span>
                        <span>{item.reason || "-"}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="ticket-detail-cell">
                  <h4>Extracted fields</h4>
                  <div className="ticket-table">
                    {selectedTicket.fields.length === 0 ? (
                      <p className="helper">No fields extracted.</p>
                    ) : selectedTicket.fields.map((item, index) => (
                      <div key={`${item.field_name}-${index}`} className="ticket-table-row">
                        <span><strong>{item.field_name}</strong></span>
                        <span>{item.field_value}</span>
                        <span>
                          {item.source}
                          {item.is_required ? " (required)" : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="ticket-detail-cell">
                  <h4>Workflow steps</h4>
                  <div className="ticket-table">
                    {selectedTicket.steps.length === 0 ? (
                      <p className="helper">No steps executed.</p>
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
                  <h4>Events</h4>
                  <div className="ticket-table">
                    {selectedTicket.events.length === 0 ? (
                      <p className="helper">No events recorded.</p>
                    ) : selectedTicket.events.map((item, index) => (
                      <div key={`${item.event_type}-${item.created_at}-${index}`} className="ticket-table-row">
                        <span><strong>{item.event_type}</strong></span>
                        <span>{item.agent_name || "-"}</span>
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

