# Dataset card: MQTT_UAD (selected)
| Field | Value |
|---|---|
| Name | MQTT_UAD, MQTT Under Attack Dataset |
| Authors / year | Aveleira-Mata, Alaiz-Moretón, Bayón-Gutiérrez, García-Ordás, Prieto-Fernández, García-Rodríguez et al., 2025 |
| Data | figshare, DOI 10.6084/m9.figshare.24420958.v1 (https://doi.org/10.6084/m9.figshare.24420958.v1) |
| Paper | Data in Brief, DOI 10.1016/j.dib.2025.112167 |
| Licence | CC BY 4.0: redistribution allowed with attribution. Not bundled here; download from the DOI page |
| Files | `DoS.csv` (94,625 frames: 45,513 attack / 49,112 normal), `MitM.csv` (110,668: 3,855 / 106,813), `Intrusion.csv` (80,893: 1,898 / 78,995) |
| Granularity | One row per network frame; 67 features per frame (per the paper abstract); real MQTT testbed in Spain |
| Size | ~79 MB (figshare listing) |

**Verified from public pages:** title, authors, year, DOI, licence, file names, frame counts, 67 features/frame.
**Not verified:** exact column names, label encoding, direct-download URL, what "Intrusion" contains. The notebook prints the columns and compares label counts to the published ones; if they differ it prints `MISMATCH`.

**Preprocessing:** label per file → class (`normal` or the file's attack); identifier/time-position columns dropped (names containing ip, mac, addr, timestamp, epoch, relative, id, stream, index, number, port); non-numeric, mostly-missing and constant columns dropped; exact duplicates removed; median imputation inside the pipeline.
**Limitations:** per-file capture sessions confound normal vs attack; frames are autocorrelated; strong imbalance in MitM/Intrusion; no brute-force/enumeration guarantee.
**Alternatives:** MQTTEEB-D (Mendeley jfttfjn6tr; licence not checked), MQTT-IoT-IDS2020 (open access, simulated), BCCC-IoT-MQTT-IDS-2025 (millions of records). Details in `backend/app/resources/dataset_manifest.json`.
Synthetic smoke-test data is generated inside the notebook (`MODE="smoke"`), flagged `is_synthetic` in all artefacts and UI.
