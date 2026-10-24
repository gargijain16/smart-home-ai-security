"""API integration tests. Require fastapi + httpx (pip install -r backend/requirements.txt); skipped otherwise."""
import io, tempfile, unittest
from pathlib import Path

import tests.conftest_helpers as H

try:
    from fastapi.testclient import TestClient
    from app.config import Settings
    from app.main import create_app
    HAVE = True
except Exception:  # noqa: BLE001
    HAVE = False


def settings(models, reports, db=":memory:"):
    return Settings(models_dir=Path(models), reports_dir=Path(reports), db_path=db,
                    cors_origins=("http://localhost:5173",), sim_seed=42, sim_tick_seconds=60.0,
                    max_upload_bytes=1024 * 1024, max_upload_rows=1000)


@unittest.skipUnless(HAVE, "fastapi/httpx not installed")
class OfflineMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.c = TestClient(create_app(settings(self.tmp, self.tmp)))

    def test_health_and_demo_mode(self):
        h = self.c.get("/api/health").json()
        self.assertEqual((h["status"], h["mode"], h["model_loaded"]), ("ok", "demo", False))
        s = self.c.get("/api/model/status").json()
        self.assertFalse(s["available"]); self.assertTrue(s["how_to_enable"])
        self.assertFalse(self.c.get("/api/model/metrics").json()["available"])

    def test_predict_returns_503_envelope_without_model(self):
        r = self.c.post("/api/predict", files={"file": ("a.csv", b"a,b\n1,2\n", "text/csv")})
        self.assertEqual(r.status_code, 503); self.assertEqual(r.json()["error"]["code"], "model_unavailable")

    def test_devices_simulation_events_flow(self):
        self.assertEqual(len(self.c.get("/api/devices").json()), 9)
        self.assertEqual(self.c.post("/api/simulation/start").json()["state"], "running")
        self.c.post("/api/simulation/step", json={"ticks": 20})
        ev = self.c.get("/api/events?label=brute_force").json()
        self.assertGreater(ev["total"], 0)
        eid = ev["items"][0]["id"]
        self.assertEqual(self.c.patch(f"/api/events/{eid}/status", json={"status": "acknowledged"}).json()["status"], "acknowledged")
        self.assertEqual(self.c.patch(f"/api/events/{eid}/status", json={"status": "nope"}).status_code, 422)
        self.assertEqual(self.c.get("/api/events/999999").status_code, 404)
        ov = self.c.get("/api/overview").json()
        self.assertEqual(ov["data_origin"], "simulated"); self.assertGreater(ov["suspicious_events"], 0)
        self.assertEqual(self.c.post("/api/simulation/reset").json()["state"], "stopped")
        self.assertEqual(self.c.get("/api/events").json()["total"], 0)

    def test_dataset_info_and_unknown_device(self):
        d = self.c.get("/api/dataset/info").json()
        self.assertIn("CC BY 4.0", d["manifest"]["selected"]["licence"])
        self.assertEqual(self.c.get("/api/devices/nope/events").status_code, 404)

    def test_cors_is_explicit(self):
        r = self.c.options("/api/health", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
        self.assertEqual(r.headers.get("access-control-allow-origin"), "http://localhost:5173")
        r = self.c.get("/api/health", headers={"Origin": "http://evil.example"})
        self.assertNotIn("access-control-allow-origin", r.headers)


@unittest.skipUnless(HAVE, "fastapi/httpx not installed")
class MlMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        art = H.smoke_artifacts()
        cls.c = TestClient(create_app(settings(art / "models", art / "reports")))
        cls.cols = [f["name"] for f in cls.c.get("/api/dataset/info").json()["feature_schema"]]

    def csv(self, rows=3, drop=None, extra=None):
        cols = [c for c in self.cols if c != drop] + ([extra] if extra else [])
        body = ",".join(cols) + "\n" + "\n".join(",".join("1.5" for _ in cols) for _ in range(rows)) + "\n"
        return {"file": ("s.csv", body.encode(), "text/csv")}

    def test_status_and_predict(self):
        self.assertTrue(self.c.get("/api/model/status").json()["is_synthetic"])
        r = self.c.post("/api/predict", files=self.csv())
        self.assertEqual(r.status_code, 200)
        j = r.json(); self.assertEqual(len(j["predictions"]), 3); self.assertTrue(j["is_synthetic_model"])

    def test_malformed_inputs(self):
        r = self.c.post("/api/predict", files=self.csv(drop=self.cols[0]))
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "schema_mismatch"))
        r = self.c.post("/api/predict", files=self.csv(extra="zzz"))
        self.assertEqual(r.status_code, 422)
        r = self.c.post("/api/predict", files={"file": ("e.csv", b"", "text/csv")})
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/predict", files={"file": ("b.csv", b"\xff\xfe\x00bad", "text/csv")})
        self.assertEqual(r.status_code, 400)

    def test_records_endpoint_and_metrics(self):
        r = self.c.post("/api/predict/records", json={"samples": [{c: 2.0 for c in self.cols}]})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(self.c.get("/api/model/metrics").json()["available"])
        self.assertEqual(self.c.get("/api/reports/confusion_matrix.png").status_code, 200)
        self.assertEqual(self.c.get("/api/reports/../../etc/passwd").status_code, 404)


if __name__ == "__main__":
    unittest.main()
