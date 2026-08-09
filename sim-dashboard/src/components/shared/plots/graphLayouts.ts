import { Data, Layout } from "plotly.js";
import colors from "tailwindcss/colors";

const baseGraphLayout: Partial<Layout> = {
  autosize: true,
  hovermode: "closest",
  title: undefined,
  colorway: [
    colors.blue[500],
    colors.purple[500],
    colors.orange[500],
    colors.green[500],
  ],
  margin: { l: 100, r: 80 },
};

export const darkModeGraphLayout: Partial<Layout> = {
  ...baseGraphLayout,
  xaxis: {
    title: "",
    titlefont: { color: colors.neutral[200] },
    gridcolor: colors.neutral[400],
    color: colors.neutral[200],
  },
  yaxis: {
    title: "",
    titlefont: { color: colors.neutral[200] },
    tickformat: ".0f",
    gridcolor: colors.neutral[400],
    color: colors.neutral[200],
  },
  plot_bgcolor: colors.neutral[800],
  paper_bgcolor: colors.neutral[800],
  titlefont: { color: colors.neutral[200] },
  legend: {
    font: { color: colors.neutral[200] },
  },
};

export const lightModeGraphLayout: Partial<Layout> = {
  ...baseGraphLayout,
  xaxis: {
    title: "",
    titlefont: { color: colors.neutral[800] },
    gridcolor: colors.neutral[500],
    color: colors.neutral[800],
  },
  yaxis: {
    title: "",
    titlefont: { color: colors.neutral[800] },
    tickformat: ".0f",
    gridcolor: colors.neutral[500],
    color: colors.neutral[800],
  },
  plot_bgcolor: colors.white,
  paper_bgcolor: colors.white,
  titlefont: { color: colors.neutral[800] },
};

export const darkDataBase: Partial<Data> = {
  gauge: {
    axis: {
      color: colors.neutral[200],
      tickcolor: colors.neutral[200],
      tickfont: { color: colors.neutral[200] },
    },
    bordercolor: colors.neutral[200],
    bar: {
      color: colors.green[600],
    },
  },
  number: {
    font: { color: colors.neutral[200] },
  },
};

export const lightDataBase: Partial<Data> = {
  gauge: {
    axis: {
      color: colors.neutral[800],
      tickcolor: colors.neutral[800],
      tickfont: { color: colors.neutral[800] },
    },
    bordercolor: colors.neutral[800],
    bar: {
      color: colors.green[600],
    },
  },
  number: {
    font: { color: colors.neutral[800] },
  },
};
