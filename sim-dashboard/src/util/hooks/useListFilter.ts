import { BaseSyntheticEvent, useState } from "react";
import { ColumnHeader } from "../../models/dataGrid/columnHeader.model";
import { FilterOperators } from "../../models/filters/filterOperators.enum";
import { cloneDeep } from "lodash";

export type onOpen = (e: BaseSyntheticEvent) => void;
export type onClose = (reset?: boolean) => void;
export type onColumnSelection = (e: BaseSyntheticEvent, index: number) => void;
export type onColumnChange = (payload: {
  index: number;
  operator: FilterOperators;
  value: string | null;
}) => void;
export type onAddColumn = (e: BaseSyntheticEvent) => void;
export type onDeleteColumn = (e: BaseSyntheticEvent, index: number) => void;
export type onApplyFilters = () => void;
export type onClearFilters = () => void;

export function useListFilter({
  columns,
  setColumns,
}: {
  columns: ColumnHeader[];
  setColumns: (columns: ColumnHeader[]) => void;
}): {
  onOpen: onOpen;
  onClose: onClose;
  onColumnSelection: onColumnSelection;
  onColumnChange: onColumnChange;
  onAddColumn: onAddColumn;
  onDeleteColumn: onDeleteColumn;
  onApplyFilters: onApplyFilters;
  onClearFilters: onClearFilters;
  isOpen: boolean;
  updatedColumns: ColumnHeader[];
  openColumn: number;
} {
  const [isOpen, setIsOpen] = useState(false);
  const [updatedColumns, setUpdatedColumns] = useState<ColumnHeader[]>([]);
  const [openColumn, setOpenColumn] = useState(0);

  function onOpen(e: BaseSyntheticEvent) {
    e.preventDefault();

    setIsOpen(true);

    const newColumns = structuredClone(columns);
    setUpdatedColumns(newColumns);
  }

  function onClose(reset?: boolean) {
    setIsOpen(false);
    setOpenColumn(0);
    if (reset) {
      setUpdatedColumns(columns);
    }
  }

  function onColumnSelection(e: BaseSyntheticEvent, index: number) {
    e.preventDefault();
    setOpenColumn(index);
  }

  function onColumnChange(payload: {
    index: number;
    operator: FilterOperators;
    value: string | null;
  }) {
    const newColumns = cloneDeep(updatedColumns);
    const column = newColumns[openColumn];
    if (payload.operator) {
      if (Object.values(FilterOperators).includes(payload.operator)) {
        column.activeFilters[payload.index].operator = payload.operator;
      }
    }
    if (payload.value !== null) {
      column.activeFilters[payload.index].value = payload.value;
    }
    setUpdatedColumns(newColumns);
  }

  function onAddColumn(e: BaseSyntheticEvent) {
    e.preventDefault();
    const newColumns = cloneDeep(updatedColumns);
    const column = newColumns[openColumn];
    if (column) {
      column.activeFilters.push({
        operator: column.operators[0],
        value: "",
      });
    }
    setUpdatedColumns(newColumns);
  }

  function onDeleteColumn(e: BaseSyntheticEvent, index: number) {
    e.preventDefault();
    const newColumns = cloneDeep(updatedColumns);
    const column = newColumns[openColumn];
    column.activeFilters.splice(index, 1);
    setUpdatedColumns(newColumns);
  }

  function onApplyFilters() {
    setColumns(
      updatedColumns.map((column) => ({
        ...column,
        activeFilters: column.activeFilters.filter((filter) => !!filter),
      })),
    );
    onClose();
  }

  function onClearFilters() {
    const newColumns = updatedColumns.map((columns) => ({
      ...columns,
      activeFilters: [],
    }));
    setColumns(newColumns);
    onClose();
  }

  return {
    onOpen,
    onClose,
    onColumnSelection,
    onColumnChange,
    onAddColumn,
    onDeleteColumn,
    onApplyFilters,
    onClearFilters,
    isOpen,
    openColumn,
    updatedColumns,
  };
}
