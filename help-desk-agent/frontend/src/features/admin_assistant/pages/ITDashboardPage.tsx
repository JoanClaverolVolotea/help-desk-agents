import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useI18n } from "../../../shared/i18n/useI18n";
import { readableError } from "../../../shared/api/errors";
import { listCategories, listTickets, listUseCases } from "../api/adminCatalogClient";
import type { CategorySummary, TicketSummary, UseCaseSummary } from "../types";

export default function ITDashboardPage(): JSX.Element {
  const { t } = useI18n();
  const [categories, setCategories] = useState<CategorySummary[]>([]);
  const [useCases, setUseCases] = useState<UseCaseSummary[]>([]);
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadAll = async (): Promise<void> => {
    setLoading(true);
    setError("");
    try {
      const [catRes, ucRes, ticketRes] = await Promise.all([
        listCategories(false),
        listUseCases(false),
        listTickets({ limit: 200, offset: 0 }),
      ]);
      setCategories(catRes.items);
      setUseCases(ucRes.items);
      setTickets(ticketRes.items);
    } catch (err) {
      setError(readableError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAll();
  }, []);

  const activeCategories = categories.filter((category) => !category.archived);
  const publishedRunbooks = useCases.filter(
    (useCase) => useCase.published_version_number !== null && !useCase.archived,
  );
  const openTickets = tickets.filter((ticket) => ticket.status === "open");
  const inProgressTickets = tickets.filter((ticket) => ticket.status === "in_progress");
  const resolvedTickets = tickets.filter((ticket) => ticket.status === "resolved");

  const ucByCategory: Record<string, UseCaseSummary[]> = {};
  for (const useCase of useCases) {
    const key = useCase.category_id || "_none";
    if (!ucByCategory[key]) {
      ucByCategory[key] = [];
    }
    ucByCategory[key].push(useCase);
  }

  const ticketsByUseCase: Record<string, TicketSummary[]> = {};
  for (const ticket of tickets) {
    const key = ticket.use_case_id || "_none";
    if (!ticketsByUseCase[key]) {
      ticketsByUseCase[key] = [];
    }
    ticketsByUseCase[key].push(ticket);
  }

  return (
    <section className="tab-panel admin-panel it-console-panel">
      <div className="admin-toolbar">
        <h2>{t("dashboardPage.title")}</h2>
        <div className="admin-toolbar-actions">
          <button type="button" className="ghost" onClick={() => void loadAll()} disabled={loading}>
            {t("common.refresh")}
          </button>
        </div>
      </div>

      {loading ? <p className="helper">{t("dashboardPage.loading")}</p> : null}
      {error ? <p className="error-text">{error}</p> : null}

      <div className="dashboard-stats">
        <div className="stat-box">
          <span className="stat-value">{activeCategories.length}</span>
          <span className="stat-label">{t("dashboardPage.statCategories")}</span>
        </div>
        <div className="stat-box">
          <span className="stat-value">{publishedRunbooks.length}</span>
          <span className="stat-label">{t("dashboardPage.statPublishedRunbooks")}</span>
        </div>
        <div className="stat-box">
          <span className="stat-value">{openTickets.length}</span>
          <span className="stat-label">{t("dashboardPage.statOpen")}</span>
        </div>
        <div className="stat-box">
          <span className="stat-value">{inProgressTickets.length}</span>
          <span className="stat-label">{t("dashboardPage.statInProgress")}</span>
        </div>
        <div className="stat-box">
          <span className="stat-value">{resolvedTickets.length}</span>
          <span className="stat-label">{t("dashboardPage.statResolved")}</span>
        </div>
      </div>

      {!loading && categories.length > 0 ? (
        <div className="hierarchy-tree">
          <h3>{t("dashboardPage.hierarchyTitle")}</h3>
          {activeCategories.map((category) => {
            const categoryUseCases = ucByCategory[category.category_id] || [];
            return (
              <details key={category.category_id} className="hierarchy-node">
                <summary>
                  <Link to={`/it/admin/use-cases?category_id=${category.category_id}`}>
                    {category.display_name}
                  </Link>
                  <span className="hierarchy-count">
                    {t("dashboardPage.runbookCount", { count: categoryUseCases.length })}
                  </span>
                </summary>
                <div className="hierarchy-children">
                  {categoryUseCases.length === 0 ? (
                    <p className="helper">{t("dashboardPage.noRunbooksUnderCategory")}</p>
                  ) : (
                    categoryUseCases.map((useCase) => {
                      const useCaseTickets = ticketsByUseCase[useCase.use_case_id] || [];
                      return (
                        <div key={useCase.use_case_id} className="hierarchy-leaf">
                          <span>{useCase.display_name}</span>
                          <div className="hierarchy-leaf-meta">
                            <span
                              className={`badge ${useCase.published_version_number ? "published" : "draft"}`}
                            >
                              {useCase.published_version_number
                                ? t("common.published")
                                : t("common.draft")}
                            </span>
                            {useCase.is_system_default ? (
                              <span className="badge default">{t("common.default")}</span>
                            ) : null}
                            <Link
                              to={`/it/admin/tickets?use_case_id=${useCase.use_case_id}`}
                              className="hierarchy-ticket-link"
                            >
                              {t("dashboardPage.ticketCount", { count: useCaseTickets.length })}
                            </Link>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </details>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
