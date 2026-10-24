# Threat model (Smart Home sector)
**Assets:** door locks, cameras, MQTT broker/gateway, home privacy and physical safety.
**Attacker:** on the home network (compromised device, guest Wi-Fi) or reaching an exposed broker; no physical access assumed.
| Threat (poster kill chain) | Impact | In dataset? | Detected by |
|---|---|---|---|
| Broker credential brute force | Full device control | Unverified | Simulator rule only |
| Wildcard topic enumeration (`#`) | Maps all controls | Unverified | Simulator rule only |
| Command publish / takeover | Lights, locks, HVAC hijacked | Unverified ("Intrusion"?) | Not evaluated |
| Connection / publish flooding (DoS) | Devices unavailable | Yes (DoS.csv) | ML model (once trained) and simulator rule |
| MitM on MQTT | Message tampering/sniffing | Yes (MitM.csv) | ML model (once trained) |
| Zigbee key sniffing, UPnP exposure, BLE relay, cloud API IDOR | Various | No | Out of scope (VAPT phase) |

**AI-specific risks:** adversarial feature manipulation to evade a tree model; dataset shift between the research testbed and a real home; false positives that lock users out if automated response were added (this project only alerts); pickle artefacts as a supply-chain risk.
**Mitigations in this project:** strict schema validation, no silent imputation of schema errors, explicit synthetic/real labelling, no automated response, explicit CORS origins, upload size/row limits.
