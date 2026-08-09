import { Outlet, createRootRouteWithContext } from "@tanstack/react-router";
import { RouterContext } from "../App";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { Nav } from "../components/shared/nav";

export const Route = createRootRouteWithContext<RouterContext>()({
  component: Root,
});

function Root() {
  return (
    <div className="flex h-screen">
      <Nav />
      <div className="flex flex-1 overflow-y-auto dark:bg-neutral-900">
        <Outlet />
      </div>
      <ReactQueryDevtools buttonPosition="top-right" />
    </div>
  );
}
