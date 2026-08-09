import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/about")({
  component: About,
});

function About() {
  return (
    <section className="flex w-full justify-center overflow-hidden">
      <div className="flex max-w-lg flex-col justify-center gap-16">
        <div className="flex flex-col gap-8 overflow-auto px-4 py-4 dark:text-neutral-200">
          <p>
            In December 2023, we have embarked upon an ambitious initiative to
            develop a comprehensive digital twin of the Frontier supercomputer.
            This twin includes: 3D asset modeling with virtual and augmented
            reality capabilities, telemetry data assimilation, AI/ML
            integration, simulations, and reinforcement learning for
            optimization. The goal was initially to develop four main modules:
          </p>
          <ol className="list-decimal pl-8">
            <li>
              A transient simulation of the thermo-fluid cooling system from
              cooling tower to cold plate.
            </li>
            <li>
              A resource allocator and power simulator - which models workloads
              and resulting dynamic power, along with energy conversion losses.
            </li>
            <li>
              A visual analytics module consisting of both an augmented reality
              model based on Unreal Engine 5, and a web-based dashboard for
              launching experiments.
            </li>
            <li>
              A network digital twin to study dynamic network power and
              congestion.
            </li>
          </ol>
          <p>
            Once we were able to model Frontier, we set out to generalize these
            modules as a generalized framework called ExaDigiT for modeling a
            variety of supercomputer architectures. This digital twin framework
            offers insights into operational strategies, “what-if” scenarios, as
            well as elucidates complex, cross-disciplinary transient behaviors.
            It also serves as a design tool for future system prototyping. Built
            on an open software stack (Modelica, SST Macro, Unreal Engine) with
            an aim to foster community-driven development, we have formed a
            partnership with supercomputer centers around the world to develop
            an open framework for modeling supercomputers.
          </p>
          <p>
            For more information please visit:{" "}
            <a href="https://exadigit.github.io/" className="text-blue-500">
              https://exadigit.github.io/
            </a>
          </p>
        </div>
      </div>
    </section>
  );
}
