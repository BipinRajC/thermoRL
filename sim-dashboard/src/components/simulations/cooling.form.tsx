import { ChangeEvent } from "react";
import { SimulationConfig } from "../../models/SimulationConfig.model";
import { Checkbox } from "../shared/checkbox";

export function CoolingForm(props: {
  form: SimulationConfig;
  setForm: (form: SimulationConfig) => void;
}) {
  return (
    <>
      <Checkbox
        label="Enabled"
        checked={props.form.cooling}
        onChange={(e: ChangeEvent<HTMLInputElement>) => {
          props.setForm({
            ...props.form,
            cooling: e.target.checked,
          });
        }}
      />
      <Checkbox
        label="Weather"
        checked={props.form.weather}
        onChange={(e: ChangeEvent<HTMLInputElement>) => {
          props.setForm({
            ...props.form,
            weather: e.target.checked,
          });
        }}
      />
    </>
  );
}
