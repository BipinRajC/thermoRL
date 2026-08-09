import { createFileRoute, Link } from "@tanstack/react-router";
import mainLogo from "../assets/logo.png";
import splashPage from "../assets/splashPage.png";

export const Route = createFileRoute("/")({
  component: Home,
});

const linkClassName =
  "rounded-md bg-neutral-200 px-4 py-2 text-neutral-900 transition-transform duration-300 ease-in-out hover:scale-105 dark:bg-neutral-800 dark:text-neutral-200";

function Home() {
  return (
    <div className="relative flex flex-1 flex-col items-center justify-center gap-4 bg-neutral-900">
      <img
        src={splashPage}
        className="absolute left-0 top-0 h-full w-full object-cover opacity-25"
      />
      <div className="relative z-10 flex flex-1 flex-col items-center justify-center gap-8 px-4 dark:text-neutral-200">
        <h1 className="text-lg  text-neutral-200">
          Welcome to the ExaDigiT dashboard!
        </h1>
        <div className="flex gap-8">
          <Link to="/about" className={linkClassName}>
            About ExaDigiT
          </Link>
          <Link to="/simulations/new" className={linkClassName}>
            New Simulation
          </Link>
          <Link to="/simulations" className={linkClassName}>
            Previous Simulations
          </Link>
        </div>
        <img
          src={mainLogo}
          className="absolute bottom-6 h-auto max-w-80 invert"
        />
      </div>
    </div>
  );
}
