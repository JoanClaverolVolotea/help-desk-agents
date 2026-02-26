import type { ReactNode } from "react";

import { useI18n } from "../i18n/useI18n";

export interface AdminTableColumn<T extends object> {
  key: string;
  label: ReactNode;
  render?: (row: T) => ReactNode;
}

interface AdminTableProps<T extends object> {
  columns: AdminTableColumn<T>[];
  rows: T[];
  emptyMessage?: string;
}

export default function AdminTable<T extends object>({
  columns,
  rows,
  emptyMessage,
}: AdminTableProps<T>): JSX.Element {
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
          {rows.map((row, rowIndex) => {
            const rowRecord = row as Record<string, unknown>;
            const rowKey = (rowRecord.id as string | number | undefined) ?? rowIndex;
            return (
              <tr key={rowKey}>
                {columns.map((col) => (
                  <td key={col.key}>
                    {col.render ? col.render(row) : (rowRecord[col.key] as ReactNode)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
