import { ArrowLongDownIcon } from "@heroicons/react/16/solid";
import { ColumnHeader } from "../../../models/dataGrid/columnHeader.model";
import { CSSProperties } from "react";
import { SortDirection } from "../../../models/filters/sortDetails.model";

function SimulationsDataGridHeaderCell({
  column,
  onSort,
  index,
}: {
  column: ColumnHeader;
  onSort: (columnName: string, direction: SortDirection) => void;
  index: number;
}) {
  return (
    <button
      className={`group flex w-full items-center justify-center gap-3 place-self-center py-3 ${index !== 0 && "border-l-2"} relative border-neutral-400 dark:border-neutral-700 dark:text-neutral-200`}
      onClick={(e) => {
        e.preventDefault();
        if (column.sort.sortable) {
          // cycle between asc/desc/no-sort
          let direction: SortDirection;
          if (column.sort.direction == "asc") {
            direction = "desc"
          } else if (column.sort.direction == "desc") {
            direction = null;
          } else {
            direction = "asc";
          }
          onSort(column.name, direction);
        }
      }}
    >
      <span>{column.name}</span>
      {column.sort.sortable && column.sort.direction ? (
        <ArrowLongDownIcon
          className={`absolute right-2 h-4 w-4 bg-neutral-300 dark:bg-neutral-800 ${column.sort.direction === "desc" && "rotate-180"} transition-opacity duration-300 ease-in-out group-hover:opacity-100`}
        />
      ) : ""}
    </button>
  );
}

export function SimulationsDataGridHeader({
  columns,
  onSort,
  style,
}: {
  columns: ColumnHeader[];
  onSort: (columnName: string, direction: SortDirection) => void;
  style: CSSProperties;
}) {
  return (
    <div
      className="grid grid-cols-9 border-b-2 border-neutral-400 bg-neutral-300 dark:border-neutral-700 dark:bg-neutral-800"
      style={{ ...style }}
    >
      {columns.map((column, index) => (
        <SimulationsDataGridHeaderCell
          key={column.name}
          column={column}
          onSort={onSort}
          index={index}
        />
      ))}
    </div>
  );
}
