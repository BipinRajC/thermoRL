import {
  AdjustmentsHorizontalIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { Modal } from "../../shared/modal";
import { ColumnHeader } from "../../../models/dataGrid/columnHeader.model";
import { useListFilter } from "../../../util/hooks/useListFilter";
import { FilterSection } from "../../shared/list/filtering/FilterSection";

export function SimulationsDataGridFilter({
  columns,
  setColumns,
}: {
  columns: ColumnHeader[];
  setColumns: (columns: ColumnHeader[]) => void;
}) {
  const {
    isOpen,
    updatedColumns,
    openColumn,
    onOpen,
    onClose,
    onColumnSelection,
    onAddColumn,
    onDeleteColumn,
    onColumnChange,
    onApplyFilters,
    onClearFilters,
  } = useListFilter({ columns, setColumns });

  const currentColumn = updatedColumns[openColumn];
  const isActiveFilters = columns.some((column) =>
    column.activeFilters.some((filter) => filter.value),
  );

  return (
    <>
      <button
        className={`flex w-full flex-1 items-center justify-center gap-2 border-b-2 border-l-2 border-neutral-400 transition-all duration-500 hover:opacity-75 dark:border-neutral-700 dark:text-neutral-200 ${isActiveFilters && "border-blue-500 bg-blue-500 text-white hover:bg-blue-500 hover:opacity-75"}`}
        onClick={onOpen}
      >
        <AdjustmentsHorizontalIcon className="h-4 w-4" />
        <span>Filters</span>
      </button>
      <Modal open={isOpen}>
        <header className="flex items-center justify-between border-b-2 px-4 py-2">
          <span className="text-lg font-medium">Simulation Filter Options</span>
          <button
            onClick={(e) => {
              e.preventDefault();
              onClose(true);
            }}
            className="transition-opacity duration-500 hover:opacity-50"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </header>
        <FilterSection
          columns={columns}
          currentColumn={currentColumn}
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
