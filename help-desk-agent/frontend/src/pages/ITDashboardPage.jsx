import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useI18n } from "../i18n/useI18n.js";
import { listCategories, listTickets, listUseCases, readableError } from "../api.js";

export default function ITDashboardPage() {
  const { t } = useI18n();
  const [categories, setCategories] = useState([]);
  const [useCases, setUseCases] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadAll = async () => {
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
    loadAll();
  }, []);

  const activeCategories = categories.filter((c) => !c.archived);
  const publishedRunbooks = useCases.filter((u) => u.published_version_number !== null && !u.archived);
  const openTickets = tickets.filter((t) => t.status === "open");
  const inProgressTickets = tickets.filter((t) => t.status === "in_progress");
  const resolvedTickets = tickets.filter((t) => t.status === "resolved");

  const ucByCategory = {};
  for (const uc of useCases) {
    const key = uc.category_id || "_none";
    if (!ucByCategory[key]) ucByCategory[key] = [];
    ucByCategory[key].push(uc);
  }

  const ticketsByUseCase = {};
  for (const t of tickets) {
    const key = t.use_case_id || "_none";
    if (!ticketsByUseCase[key]) ticketsByUseCase[key] = [];
    ticketsByUseCase[key].push(t);
  }

  return (
    <section className="tab-panel admin-panel it-console-panel">
      <div className="admin-toolbar">
        <h2>{t("dashboardPage.title")}</h2>
        <div className="admin-toolbar-actions">
          <button type="button" className="ghost" onClick={loadAll} disabled={loading}>
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
          {activeCategories.map((cat) => {
            const catUseCases = ucByCategory[cat.category_id] || [];
            return (
              <details key={cat.category_id} className="hierarchy-node">
                <summary>
                  <Link to={`/it/admin/use-cases?category_id=${cat.category_id}`}>
                    {cat.display_name}
                  </Link>
                  <span className="hierarchy-count">
                    {t("dashboardPage.runbookCount", { count: catUseCases.length })}
                  </span>
                </summary>
                <div className="hierarchy-children">
                  {catUseCases.length === 0 ? (
                    <p className="helper">{t("dashboardPage.noRunbooksUnderCategory")}</p>
                  ) : (
                    catUseCases.map((uc) => {
                      const ucTickets = ticketsByUseCase[uc.use_case_id] || [];
                      return (
                        <div key={uc.use_case_id} className="hierarchy-leaf">
                          <span>{uc.display_name}</span>
                          <div className="hierarchy-leaf-meta">
                            <span className={`badge ${uc.published_version_number ? "published" : "draft"}`}>
                              {uc.published_version_number ? t("common.published") : t("common.draft")}
                            </span>
                            {uc.is_system_default ? (
                              <span className="badge default">{t("common.default")}</span>
                            ) : null}
                            <Link
                              to={`/it/admin/tickets?use_case_id=${uc.use_case_id}`}
                              className="hierarchy-ticket-link"
                            >
                              {t("dashboardPage.ticketCount", { count: ucTickets.length })}
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
