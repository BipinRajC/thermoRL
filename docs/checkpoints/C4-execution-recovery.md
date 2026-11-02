# E12 operational recovery authorization

**Date:** 2026-10-31. **Authorizing instruction from Bipin:** "dont stop, resume wherever it stopped". This follows the report of controller SIGTERM, four validated runs, three partial attempts and eight unstarted configurations.

## Operational interpretation needed to resume

- Preserve and reuse the four validated primary runs. Do not overwrite them.
- Archive the three interrupted attempts and restart each exactly once, alongside the eight unstarted configurations. This yields 15 successful primary configurations, three retained interrupted attempts, and the one already planned fresh-process TP seed1 repeat: **19 cumulative process attempts, including the three abandoned attempts**, rather than hiding them in a claim of 16 total starts.
- The controller stopped after approximately45minutes with SIGTERM; the exact origin remains unresolved. A transient user systemd service with no runtime deadline isolates the resumed controller from interactive command lifetime. No automatic service or simulation retry is enabled.
- Necessary source changes are restricted to orchestration recovery, retry accounting and the guard's recognition of explicitly recorded interrupted attempts. No workload, cache, seed, rho, horizon, warm-up, policy, scorer, spanning, RAPS, FMU, thermal backend, G1 or primary-metric/success-rule change.
- The four retained runs keep their original launch SHA18dfea1 and source maps. Their numerical decision/thermal paths are unchanged. The incomplete TP seed1 run has no completed manifest and will be restarted under the recovery launch commit; its later fresh-process comparison must match that new commit/source/environment exactly. **No C′ comparison precondition or equality criterion is relaxed.**
- Resume and final metadata distinguish controller generations, physical attempts, selected successful configurations and aborted attempts. Original journal entries and interrupted artifacts remain preserved; no synthetic completion events are invented.
- Freeze the recovery source after tested commits and before any resumed simulation. Do not commit again until C′ evidence is generated, keeping its exact Git precondition viable.

## Limits

This authorizes only operational completion of the existing experiment following the resume instruction. It is not a new research direction, policy comparison, E11 rerun, workload tuning or authorization for additional retries after this recovery. Any actual scientific/invariant failure still stops without fallback or tolerance changes. Stop at C4 after report, commit and push.
