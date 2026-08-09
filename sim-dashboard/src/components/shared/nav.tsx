import * as React from "react";
import { useContext, useState } from "react" 
import { AppContext } from "../../App";
import {
  BeakerIcon as BeakerOutlinedIcon,
  BookOpenIcon,
  ChevronDoubleRightIcon,
  MoonIcon,
  PlusIcon,
  SunIcon,
} from "@heroicons/react/24/outline";
import {
  BeakerIcon,
  BookOpenIcon as BookOpenSolidIcon,
} from "@heroicons/react/24/solid";
import { Tooltip } from "react-tooltip";
import logo from "../../assets/smallLogo.png";
import { Link, createLink } from "@tanstack/react-router";
import logoText from "../../assets/logoText.png";

export function Nav() {
  const navbar = localStorage.getItem("navbar-size") as
    | "small"
    | "large"
    | null;
  const [navbarSize, setNavbarSize] = useState<"small" | "large">(
    navbar ? navbar : "small",
  );
  const { theme, setTheme } = useContext(AppContext);

  return (
    <div
      className={`flex flex-col overflow-hidden bg-neutral-200 pb-6 pt-2 shadow-md transition-all duration-300 ease-in-out dark:bg-neutral-800 ${navbarSize === "small" ? "w-12" : "w-48"}`}
    >
      <Link
        to="/"
        params={{}}
        search={{}}
        data-tooltip-id="home-icon-tooltip"
        data-tooltip-content={"ExaDigiT"}
        data-tooltip-delay-show={500}
        data-tooltip-hidden={navbar === "large"}
        className="p-3 hover:bg-transparent dark:hover:bg-transparent"
      >
        <div className="flex items-center gap-4">
          <img src={logo} className="min-h-6 w-6 dark:invert" />
          <img
            src={logoText}
            className="h-6 overflow-hidden object-contain dark:invert"
          />
        </div>
      </Link>
      <StyledLink
        to="/simulations"
        params={{}}
        search={{}}
        data-tooltip-id="simulations-icon-tooltip"
        data-tooltip-content={"Simulations List"}
        data-tooltip-delay-show={500}
        data-tooltip-hidden={navbar === "large"}
      >
        {({ isActive }) => (
          <>
            {isActive ? (
              <BeakerIcon className="size-6 min-w-6" />
            ) : (
              <BeakerOutlinedIcon className="size-6 min-w-6" />
            )}
            Simulations
          </>
        )}
      </StyledLink>
      <StyledLink
        to="/simulations/new"
        params={{}}
        search={{}}
        data-tooltip-id="new-simulation-icon-tooltip"
        data-tooltip-content={"New Simulation"}
        data-tooltip-delay-show={500}
        data-tooltip-hidden={navbar === "large"}
      >
        <PlusIcon className="size-6 min-w-6" />
        New Simulation
      </StyledLink>
      <div className="mt-auto flex flex-col text-neutral-800 dark:text-neutral-200">
        <StyledLink
          to="/about"
          params={{}}
          search={{}}
          data-tooltip-id="about-icon-tooltip"
          data-tooltip-content={"About"}
          data-tooltip-delay-show={500}
          data-tooltip-hidden={navbar === "large"}
        >
          {({ isActive }) => (
            <>
              {isActive ? (
                <BookOpenSolidIcon className="size-6 min-w-6" />
              ) : (
                <BookOpenIcon className="size-6 min-w-6" />
              )}
              About
            </>
          )}
        </StyledLink>
        <button
          className="flex gap-4 overflow-hidden whitespace-nowrap p-3 transition-colors duration-500 ease-in-out hover:bg-neutral-300 dark:hover:bg-neutral-700"
          onClick={(e) => {
            e.preventDefault();
            if (!theme || theme === "dark") {
              localStorage.setItem("graph-theme", "light");
              setTheme("light");
            } else {
              localStorage.setItem("graph-theme", "dark");
              setTheme("dark");
            }
          }}
          data-tooltip-id="dark-light-mode-tooltip"
          data-tooltip-content="Toggle Light or Dark Mode"
          data-tooltip-delay-show={1000}
        >
          {!theme || theme === "dark" ? (
            <MoonIcon className="size-6 min-w-6" />
          ) : (
            <SunIcon className="size-6 min-w-6" />
          )}
          Toggle {theme === "light" ? "Dark" : "Light"} Mode
        </button>
        <button
          className="flex gap-4 overflow-hidden whitespace-nowrap p-3 transition-colors duration-500 ease-in-out hover:bg-neutral-300 dark:hover:bg-neutral-700"
          onClick={(e) => {
            e.preventDefault();
            if (navbarSize === "small") {
              localStorage.setItem("navbar-size", "large");
              setNavbarSize("large");
            } else {
              localStorage.setItem("navbar-size", "small");
              setNavbarSize("small");
            }
          }}
        >
          <ChevronDoubleRightIcon
            className={`size-6 min-w-6 ${navbarSize === "small" ? "" : "rotate-180"}`}
          />
          Collapse
        </button>
      </div>
      <Tooltip id="dark-light-mode-tooltip" className="z-50" />
      <Tooltip id="home-icon-tooltip" className="z-50" />
      <Tooltip id="about-icon-tooltip" className="z-50" />
      <Tooltip id="simulations-icon-tooltip" className="z-50" />
      <Tooltip id="new-simulation-icon-tooltip" className="z-50" />
    </div>
  );
}


export const StyledLink = createLink(
  React.forwardRef((props, ref: React.ForwardedRef<HTMLAnchorElement>) => {
    return (
      <Link
        {...props}
        ref={ref}
        className={
          `flex flex-nowrap gap-4 whitespace-nowrap px-3 py-3 text-neutral-800 transition-colors duration-500 ease-in-out hover:bg-neutral-300 dark:text-neutral-200 dark:hover:bg-neutral-700 dark:hover:text-neutral-300 ${(props as any).className ?? ''}`
        }
        activeProps={{
          className: `dark:bg-neutral-600 bg-neutral-300`,
        }}
        activeOptions={{ exact: true, includeHash: false, includeSearch: true }}
    />
    )
  }),
)