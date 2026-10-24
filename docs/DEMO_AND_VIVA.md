# Five-minute demo script
1. **0:00** Problem: smart homes, MQTT, poster kill chain (30 s).
2. **0:30** Overview in demo mode. Point at the "Simulated data" banner and "Demo mode, no trained model" badge. Press Start.
3. **1:15** Devices: floor plan, a lock turns red during the brute-force phase; open its draggable detail window.
4. **2:00** Events: filter by `brute_force`, inspect an event, mark it acknowledged. Say plainly: rule-based, not ML.
5. **2:45** AI detection: show the schema rules, upload a CSV with a wrong column → clear rejection; upload a valid one → predictions, vote share, evidence. (Say whether the model is real or the synthetic check.)
6. **3:45** Evaluation + Dataset pages: per-class table, confusion matrix, FPR/FNR, limitations, provenance and licence.
7. **4:30** Roadmap: VAPT module slots in; close.
Rehearse once with the backend on the same network; keep a tunnel or deployed URL ready.

# Presentation outline
Title · Problem and threat model · Dataset (MQTT_UAD, licence, limits) · Method (split, imbalance, leakage) · Architecture · Live demo · Results with limitations · Honest scope (real vs simulated) · Future VAPT work · Q&A.

# Viva questions and answers
- **Why not accuracy alone?** Normal traffic dominates; a model can score high accuracy and miss every rare attack. Macro-F1, per-class recall and FNR expose that.
- **Why block splitting?** Adjacent frames are near-duplicates; a random split lets the model memorise neighbours and inflates test scores.
- **Why Random Forest vs Decision Tree?** Chosen on validation macro-F1, not on test. Trees need no scaling and are inspectable; RF reduces variance.
- **Is the vote share a probability?** No: uncalibrated; labelled so.
- **Why are dashboard events not scored by the model?** They have no frame-level features; claiming otherwise would be fabrication. Rules label them and say so.
- **What if the real dataset has different columns?** The notebook prints them, checks counts, and the API enforces the exported schema exactly.
- **How could an attacker evade it?** Craft traffic whose features look normal (adversarial/mimicry), exploit dataset shift. Mitigation: retrain on lab attacks, ensemble, rate rules.
- **Why alert-only?** Automated response risks locking residents out of their own home.
- **What is missing?** Real-data results, live MQTT ingestion, VAPT, calibration, and brute-force/enumeration coverage in the data.
