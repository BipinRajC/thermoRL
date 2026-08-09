import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { ChangeEvent, useState } from "react";
import { RAPSForm } from "../components/simulations/raps.form";
import { BasicSettingsForm } from "../components/simulations/basicSettings.form";
import { Button } from "../components/shared/button";
import { CoolingForm } from "../components/simulations/cooling.form";
import { SimulationConfig, getDefaultSimulationConfig } from "../models/SimulationConfig.model";
import { TextArea } from "../components/shared/textArea"
import { ArrowLeftIcon } from "@heroicons/react/24/outline";
import { useMutation } from "@tanstack/react-query";
import { tryParseYaml } from "../util/misc";
import axios from "axios";
import { Section } from "../components/shared/simulation/section";
import { Simulation } from "../models/Simulation.model";

export const Route = createFileRoute("/simulations/new")({
  component: NewSimultation,
});

function NewSimultation() {
  const [form, setForm] = useState(getDefaultSimulationConfig);
  const [advancedStr, setAdvancedStr] = useState("");
  const navigate = useNavigate();

  const onSubmit = useMutation({
    mutationFn: async ({ form }: { form: SimulationConfig }) => {
      const advancedConfig = tryParseYaml(advancedStr)[0]
      const sim = await axios.post<Simulation>(
        "/simulation/run",
        advancedConfig ?? form,
      );
      navigate({
        to: `/simulations/$simulationId/summary`,
        params: { simulationId: sim.data.id },
        search: {
          playbackInterval: 15,
        },
      });
    },
  });

  return (
    <div className="m-6 flex flex-1 flex-col justify-center">
      <div className="flex items-center justify-between">
        <Link
          to="/simulations"
          className="flex items-center gap-2 self-start transition-opacity duration-500 hover:opacity-75 dark:text-neutral-200"
        >
          <ArrowLeftIcon className="h-6 w-6" />
          <span>Back to List</span>
        </Link>
        <h1 className="text-xl font-medium dark:text-neutral-200">
          New Simulation
        </h1>
      </div>
      <div className="mt-6 flex flex-1 flex-col rounded-lg bg-neutral-200 p-8 shadow-md dark:bg-neutral-800">
        <div className="my-6 flex flex-1 flex-col gap-6">
          <Section
            header="Base Settings"
            sectionProps={{ className: "grid-cols-3 gap-x-2" }}
            alwaysOpen
          >
            <BasicSettingsForm form={form} setForm={setForm} />
          </Section>
          <Section
            header="RAPS Configuration"
            sectionProps={{ className: "grid-cols-3 gap-x-2" }}
          >
            <RAPSForm form={form} setForm={setForm} />
          </Section>
          <Section
            header="Cooling Configuration"
            sectionProps={{ className: "grid-cols-3 gap-x-2" }}
          >
            <CoolingForm form={form} setForm={setForm} />
          </Section>
          <Section
            header="Advanced Configuration (YAML)"
            sectionProps={{ className: "grid-cols-1" }}
            defaultExpanded={false}
          >
              <TextArea
                value={advancedStr}
                onChange={(e: ChangeEvent<HTMLTextAreaElement>) => {
                  setAdvancedStr(e.target.value);
                }}
                className="h-[25vh]"
                error={tryParseYaml(advancedStr)[1]}
              />
          </Section>
        </div>
        <footer className="flex justify-end">
          <Button
            variant="filled"
            type="submit"
            onClick={async (e) => {
              e.preventDefault();
              await onSubmit.mutateAsync({ form });
            }}
            disabled={onSubmit.isPending}
          >
            {onSubmit.isPending ? "Submitting..." : "Submit"}
          </Button>
        </footer>
      </div>
    </div>
  );
}
