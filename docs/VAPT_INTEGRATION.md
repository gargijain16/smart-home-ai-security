# Future VAPT integration plan (not implemented)
The nav item is disabled. Planned, additive-only integration:
1. **Router + service:** `routes/vapt.py` and `services/vapt/` behind a scope/rules-of-engagement check (target allowlist limited to the team's own lab).
2. **Nmap discovery:** wrap `nmap -sV -p 1883,8883` against the lab network; store raw XML plus parsed services in a new `findings` table with evidence (command, timestamp, output hash).
3. **MQTT checks:** anonymous-connect, weak-credential and wildcard-subscribe tests against the team's own Mosquitto only, mirroring the poster kill chain.
4. **Scoring:** CVSS v3.1 calculator per finding; prioritised list; exploit → mitigate → re-test evidence.
5. **Bridge to AI:** feed captured traffic from the lab attacks into the notebook as new labelled data, then retrain and compare.
6. **UI:** enable the nav item and add a page using the same `Panel`, `Pill` and typed-API patterns. No existing page changes. Live ingestion and extra models follow the same pattern (`services/` + typed `schemas.py` + `types/api.ts`).
