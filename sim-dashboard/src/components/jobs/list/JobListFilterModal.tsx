import {
  AdjustmentsHorizontalIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { Tooltip } from "react-tooltip";
import { Modal } from "../../shared/modal";
import { ColumnHeader } from "../../../models/dataGrid/columnHeader.model";
import { FilterSection } from "../../shared/list/filtering/FilterSection";
import { useListFilter } from "../../../util/hooks/useListFilter";

export function JobListFilterModal({
  columns,
  setColumns,
}: {
  columns: ColumnHeader[];
  setColumns: (newColumns: ColumnHeader[]) => void;
}) {
  const {
    isOpen,
    openColumn,
    updatedColumns,
    onOpen,
    onClose,
    onColumnSelection,
    onColumnChange,
    onDeleteColumn,
    onAddColumn,
    onApplyFilters,
    onClearFilters,
  } = useListFilter({ columns, setColumns });

  const isActiveFilters = columns.some((column) =>
    column.activeFilters.some((filter) => filter.value),
  );

  return (
    <>
      <button
        className={`rounded-full px-2 py-2 transition-colors duration-500 hover:bg-neutral-300 dark:hover:bg-neutral-700 ${isActiveFilters ? "text-blue-500" : "dark:text-neutral-200 "}`}
        data-tooltip-id="filter-tooltip"
        data-tooltip-content={"Open Filter Dialog"}
        data-tooltip-delay-show={500}
        onClick={onOpen}
      >
        <AdjustmentsHorizontalIcon className="h-6 w-6" />
      </button>
      <Tooltip id="filter-tooltip" />
      <Modal open={isOpen}>
        <header className="flex items-center justify-between border-b-2 px-4 py-2">
          <span className="text-lg font-medium">Job List Filter Options</span>
          <button
            onClick={(e) => {
              e.preventDefault();
              onClose();
            }}
            className="transition-opacity duration-500 hover:opacity-50"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </header>
        <FilterSection
          columns={columns}
          currentColumn={updatedColumns[openColumn]}
          onAddColumn={onAddColumn}
          onApplyFilters={onApplyFilters}
          onClose={onClose}
          onColumnChange={onColumnChange}
          onColumnSelection={onColumnSelection}
          onDeleteColumn={onDeleteColumn}
          openColumn={openColumn}
          onClearFilters={onClearFilters}
        />
      </Modal>
    </>
  );
}
