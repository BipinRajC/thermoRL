import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import Keycloak, { KeycloakConfig } from "keycloak-js";
import { createContext, useEffect, useState } from "react";
import axios from "axios";

import { routeTree } from "./routeTree.gen";
import { LoadingSpinner } from "./components/shared/loadingSpinner";

import "react-datepicker/dist/react-datepicker.css";
import "react-tooltip/dist/react-tooltip.css";

const basepath = import.meta.env.VITE_BASE_PATH
  ? new URL(import.meta.env.VITE_BASE_PATH).pathname
  : "/";
axios.defaults.baseURL = import.meta.env.VITE_API_PATH;

export { axios };

export interface RouterContext {
  queryClient: QueryClient;
}

const queryClient = new QueryClient();
const router = createRouter({
  routeTree,
  context: { queryClient },
  defaultPendingComponent: LoadingSpinner,
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export const AppContext = createContext<{
  theme: string | null;
  setTheme: (value: "dark" | "light") => void;
}>({ theme: null, setTheme: () => {} });

function App() {
  const [apiToken, setApiToken] = useState<string>();
  const [theme, setTheme] = useState(localStorage.getItem("theme"));

  const onThemeSwitch = (theme: "dark" | "light") => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }

    localStorage.setItem("theme", theme);
    setTheme(theme);
  };

  useEffect(() => {
    if (
      localStorage.theme === "dark" ||
      (!("theme" in localStorage) &&
        window.matchMedia("(prefers-color-scheme: dark)").matches)
    ) {
      onThemeSwitch("dark");
    } else {
      onThemeSwitch("light");
    }
  }, []);

  useEffect(() => {
    if (!apiToken && import.meta.env.VITE_AUTH_URL) {
      const initOptions: KeycloakConfig = {
        url: import.meta.env.VITE_AUTH_URL,
        realm: "obsidian",
        clientId: "obsidian-public",
      };

      const kc = new Keycloak(initOptions);

      kc.init({
        onLoad: "login-required",
        redirectUri: window.location.toString(),
      }).then(
        (auth) => {
          if (auth) {
            if (kc.token) {
              axios.defaults.headers.common = {
                Authorization: `Bearer ${kc.token}`,
              };
              axios.defaults.withCredentials = true;
              setApiToken(kc.token)
            }
          }
        },
        () => {
          console.error("Authenticated Failed");
        },
      );

      setApiToken(apiToken)
    } else {
      setApiToken("no-auth")
    }
  }, [apiToken])

  if (!apiToken) {
    return <h1>Please Authenticate</h1>;
  }

  return (
    <AppContext.Provider value={{ theme: theme, setTheme: onThemeSwitch }}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} basepath={basepath} />
      </QueryClientProvider>
    </AppContext.Provider>
  );
}

export default App;
