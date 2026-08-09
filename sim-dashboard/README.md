## About The Project

User Interface for the ExaDigiT project that allows for running simulations and seeing the metrics that are produced.

### Built With

[![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB)](https://react.dev)

![TypeScript](https://img.shields.io/badge/typescript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white)

[![TailwindCSS](https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)

[![Plotly](https://img.shields.io/badge/plotly-%233F4F75.svg?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/graphing-libraries/)

[Tanstack](https://tanstack.com/)

## Running Locally

To get the project up and running locally, clone and deploy the SimulationServer from [GitHub](https://github.com/ExaDigiT/SimulationServer)
or [GitLab](https://code.ornl.gov/exadigit/simulationserver) and follow the instructions to launch a local instance of the full server and
dashboard stack. The dashboard will be hosted on http://localhost:8080 by default.

You can also run the ExaDigiT dashboard directly, e.g. for faster development builds or to run it against an existing ExaDigiT Simulation Server deployment.
Run the simulation server locally without the dashboard by running this in `simulation-server`:
```bash
docker compose up simulation-server --wait
```

Then in `simulation-dashboard` run:
```bash
npm install
npm run dev
```

After doing so you can navigate to http://localhost:8080 to use the application.
