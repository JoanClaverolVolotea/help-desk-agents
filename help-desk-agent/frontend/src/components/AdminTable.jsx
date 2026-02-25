import { useI18n } from "../i18n/useI18n.js";

export default function AdminTable({ columns, rows, emptyMessage }) {
  const { t } = useI18n();
  const resolvedEmptyMessage = emptyMessage ?? t("common.noData");

  if (rows.length === 0) {
    return <div className="empty-state">{resolvedEmptyMessage}</div>;
  }

  return (
    <div className="admin-table-wrapper">
      <table className="admin-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={row.id ?? rowIndex}>
              {columns.map((col) => (
                <td key={col.key}>{col.render ? col.render(row) : row[col.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
