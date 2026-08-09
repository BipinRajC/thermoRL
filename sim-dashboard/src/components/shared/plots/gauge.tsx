import { useContext } from "react";
import ReactGauge from "react-gauge-component";
import { AppContext } from "../../../App";
import { GaugeComponentProps } from "react-gauge-component/dist/lib/GaugeComponent/types/GaugeComponentProps";
import { merge } from "lodash";
import colors from "tailwindcss/colors";

const lightGauge: Partial<GaugeComponentProps> = {
  labels: {
    tickLabels: {
      defaultTickLineConfig: { color: colors.neutral[900] },
      defaultTickValueConfig: { style: { fill: colors.neutral[900] } },
    },
    valueLabel: {
      style: {
        fill: colors.neutral[800],
        fontWeight: "bold",
        textShadow: "unset",
      },
    },
  },
};

const darkGauge: Partial<GaugeComponentProps> = {
  labels: {
    valueLabel: {
      style: {
        fontWeight: "bold",
        textShadow: "unset",
      },
    },
  },
};

export function Gauge(props: Partial<GaugeComponentProps>) {
  const { theme } = useContext(AppContext);

  const baseGauge = theme === "light" ? lightGauge : darkGauge;

  const gauge = {};
  merge(gauge, baseGauge, props);

  return <ReactGauge key={theme} {...gauge} />;
}
