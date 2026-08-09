import { Data, Layout } from "plotly.js";
import { useContext } from "react";
import Plot from "react-plotly.js";
import { AppContext } from "../../../App";
import {
  darkDataBase,
  darkModeGraphLayout,
  lightDataBase,
  lightModeGraphLayout,
} from "./graphLayouts";
import { merge } from "lodash";

export function Graph({
  data,
  layout,
}: {
  data: Partial<Data>[];
  layout?: Partial<Layout>;
}) {
  const { theme } = useContext(AppContext);
  const currentLayout =
    theme === "light" ? lightModeGraphLayout : darkModeGraphLayout;
  const currentDataBase = theme === "light" ? lightDataBase : darkDataBase;

  const _layout = {};
  merge(_layout, currentLayout, layout);

  const _data: Partial<Data>[] = data.map((d) => {
    const mergedData = {};
    merge(mergedData, currentDataBase, d);
    return mergedData;
  });

  return (
    <Plot
      layout={{
        ..._layout,
      }}
      data={_data}
      className="w-full"
      config={{ displaylogo: false }}
    />
  );
}
