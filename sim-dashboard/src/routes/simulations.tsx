import { Outlet, createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/simulations")({
  component: Simulations,
});

function Simulations() {
  return (
    <>
      <Outlet />
    </>
  );
}
