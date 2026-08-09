import { ChangeEvent } from "react";
import * as iso8601 from "iso8601-duration";
import {
  SimulationConfig, WorkloadType, workloadTypes, schedulers, SchedulerType,
} from "../../models/SimulationConfig.model";
import { Select } from "../shared/dropdown";
import { NumberInput } from "../shared/number";

export function RAPSForm(props: {
  form: SimulationConfig;
  setForm: (form: SimulationConfig) => void;
}) {
  return (
    <>
      <Select
        label="Workload Mode"
        choices={workloadTypes.map(w => ({ label: w, value: w }))}
        value={props.form.workload}
        onChange={(e) => {
          const workload = e.target.value as WorkloadType;
          if (workload == "replay") {
            props.setForm({
              ...props.form,
              workload: "replay",
              arrival: "prescribed",
              numjobs: undefined,
              seed: undefined,
              replay: true,
              scheduler: "default",
              policy: "replay",
            })
          } else {
            props.setForm({
              ...props.form,
              workload: workload,
              arrival: "prescribed",
              replay: false,
              policy: props.form.policy == 'replay' ? 'fcfs' : props.form.policy,
            })
          }
        }}
      />
      {props.form.workload == "replay" ? (<>
        <Select
          label="Reschedule Arrival"
          choices={[
            { label: "prescribed", value: "prescribed" },
            { label: "poisson", value: "poisson" },
          ]}
          value={props.form.policy}
          onChange={(e) => {
            props.setForm({
              ...props.form,
              arrival: e.target.value as "prescribed" | "poisson",
            });
          }}
        />
      </>) : (<>
          <NumberInput
            inputProps={{ // TODO handle invalid inputs better
              onChange: (e: ChangeEvent<HTMLInputElement>) => {
                const value = parseInt(e.target.value)
                props.setForm({
                  ...props.form,
                  numjobs: isNaN(value) ? undefined : value,
                });
              },
              value: props.form.numjobs ?? "",
            }}
            label="Number of Jobs"
            className="row-start-2"
          />
          <NumberInput
            label="Seed"
            inputProps={{
              onChange: (e: ChangeEvent<HTMLInputElement>) => {
                const value = parseInt(e.target.value);
                props.setForm({
                  ...props.form,
                  seed: isNaN(value) ? undefined : value,
                });
              },
              value: props.form.seed ?? "",
            }}
            className="row-start-2"
          />
          <Select
            label="Scheduler"
            choices={Object.keys(schedulers).map(s => ({ label: s, value: s }))}
            value={props.form.scheduler}
            onChange={(e) => {
              const scheduler = e.target.value as SchedulerType
              let policy = props.form.policy;
              if (!schedulers[scheduler].policies.includes(props.form.policy)) {
                policy = "fcfs"
              }
              props.setForm({ ...props.form, scheduler, policy });
            }}
          />
          <Select
            label="Schedule Policy"
            choices={schedulers[props.form.scheduler].policies.map(p => ({ label: p, value: p }))}
            value={props.form.policy}
            onChange={(e) => {
              props.setForm({
                ...props.form,
                policy: e.target.value,
              });
            }}
          />
      </>)}
      <NumberInput
        inputProps={{
          onChange: (e: ChangeEvent<HTMLInputElement>) => {
            let value = parseInt(e.target.value)
            value = isNaN(value) ? 1 : value,
            props.setForm({
              ...props.form,
              time_delta: `PT${value}S`,
            });
          },
          value: iso8601.toSeconds(iso8601.parse(props.form.time_delta)),
        }}
        label="Time Delta"
      />
    </>
  );
}
