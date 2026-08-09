export type GridSizes = "small" | "medium" | "large";

export function getGridSize(size: GridSizes) {
  switch (size) {
    case "small":
      return "col-span-1";
    case "medium":
      return "col-span-2";
    case "large":
      return "col-span-3";
  }
}
