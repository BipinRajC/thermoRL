import { addMinutes } from "date-fns";
import { SimulationConfig } from "../../models/SimulationConfig.model";
import { SharedDatePicker } from "../shared/datepicker";
import { Select } from "../shared/dropdown";
import { useQuery } from "@tanstack/react-query";
import { getSystems } from "../../util/queryOptions";
import { LoadingSpinner } from "../shared/loadingSpinner";

export function BasicSettingsForm({
  form,
  setForm,
}: {
  form: SimulationConfig;
  setForm: (form: SimulationConfig) => void;
}) {
  const { data: systems } = useQuery(getSystems());
  if (!systems) {
    return <LoadingSpinner/>
  }

  return (
    <>
      <SharedDatePicker
        label="Start Date"
        onChange={(newDate) => {
          if (newDate) {
            let endDate = form.end;
            if (new Date(newDate) >= new Date(form.end)) {
              endDate = addMinutes(newDate, 60).toISOString();
            }
            setForm({ ...form, start: newDate, end: endDate });
          }
        }}
        value={form.start}
      />
      <SharedDatePicker
        key={form.end}
        label="End Date"
        onChange={(newDate) => {
          setForm({ ...form, end: newDate || "" });
        }}
        value={form.end}
        boundedDate={new Date(form.start)}
      />
      <Select
        label="System"
        choices={systems.map(system => ({ label: system.name, value: system.name }))}
        value={form.system}
        onChange={(e) => {
          setForm({
            ...form,
            system: e.target.value,
          });
        }}
      />
    </>
  );
}
