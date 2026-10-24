import json, tempfile, unittest
from pathlib import Path

import pandas as pd

from tests.conftest_helpers import smoke_artifacts
from app.services.ml_service import ModelService, ModelUnavailable, SchemaError


class NoModel(unittest.TestCase):
    def test_missing_model_reports_demo_mode(self):
        with tempfile.TemporaryDirectory() as d:
            svc = ModelService(Path(d), Path(d))
            self.assertFalse(svc.loaded)
            st = svc.status()
            self.assertFalse(st["available"]); self.assertEqual(st["mode"], "demo")
            self.assertTrue(st["how_to_enable"])
            with self.assertRaises(ModelUnavailable):
                svc.require()
            self.assertFalse(svc.metrics()["available"])

    def test_corrupt_metadata_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "model_metadata.json").write_text("{not json")
            (Path(d) / "smart_home_ids_pipeline.joblib").write_bytes(b"junk")
            svc = ModelService(Path(d), Path(d))
            self.assertFalse(svc.loaded); self.assertIn("failed to load", svc.error.lower())


class WithSmokeModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        art = smoke_artifacts()
        cls.svc = ModelService(art / "models", art / "reports")
        cls.art = art

    def sample(self, n=5):
        return pd.DataFrame([{f: 1.0 + i for f in self.svc.feature_names} for i in range(n)])

    def test_loads_and_flags_synthetic(self):
        self.assertTrue(self.svc.loaded)
        st = self.svc.status()
        self.assertTrue(st["is_synthetic"]); self.assertFalse(st["is_benchmark"])
        self.assertEqual(st["mode"], "ml"); self.assertIn("normal", st["classes"])

    def test_metadata_has_schema_and_provenance(self):
        m = json.loads((self.art / "models" / "model_metadata.json").read_text())
        for k in ("features", "classes", "dataset", "evaluation", "model_version", "environment", "limitations"):
            self.assertIn(k, m)
        self.assertIn("SYNTHETIC", m["dataset"]["name"])

    def test_prediction_shape_and_provenance(self):
        out = self.svc.predict_frame(self.sample(4))
        self.assertEqual(len(out["predictions"]), 4)
        self.assertEqual(out["model_version"], self.svc.metadata["model_version"])
        self.assertTrue(out["is_synthetic_model"]); self.assertIn("predicted_at", out)
        self.assertEqual(sum(out["summary"].values()), 4)
        p = out["predictions"][0]
        self.assertIn(p["predicted_class"], self.svc.metadata["classes"])
        self.assertEqual(len(p["evidence"]), 5)

    def test_rejects_missing_unexpected_columns(self):
        df = self.sample().drop(columns=[self.svc.feature_names[0]])
        with self.assertRaises(SchemaError) as cm:
            self.svc.predict_frame(df)
        self.assertEqual(cm.exception.details["missing"], [self.svc.feature_names[0]])
        df = self.sample(); df["extra_col"] = 1
        with self.assertRaises(SchemaError) as cm:
            self.svc.predict_frame(df)
        self.assertEqual(cm.exception.details["unexpected"], ["extra_col"])

    def test_rejects_non_numeric_inf_and_empty(self):
        df = self.sample().astype(object); df.iloc[1, 0] = "abc"
        with self.assertRaises(SchemaError): self.svc.predict_frame(df)
        df = self.sample(); df.iloc[0, 0] = float("inf")
        with self.assertRaises(SchemaError): self.svc.predict_frame(df)
        with self.assertRaises(SchemaError): self.svc.predict_frame(self.sample(0))

    def test_missing_cells_are_reported_not_hidden(self):
        df = self.sample(); df.iloc[0, 0] = None
        out = self.svc.predict_frame(df)
        self.assertEqual(out["validation"]["rows_with_missing_values"], 1)

    def test_column_order_is_enforced(self):
        df = self.sample()[list(reversed(self.svc.feature_names))]
        a = self.svc.predict_frame(df)["predictions"]; b = self.svc.predict_frame(self.sample())["predictions"]
        self.assertEqual([x["predicted_class"] for x in a], [x["predicted_class"] for x in b])

    def test_metrics_come_from_saved_files(self):
        mt = self.svc.metrics()
        self.assertTrue(mt["available"])
        saved = json.loads((self.art / "reports" / "model_metrics.json").read_text())
        self.assertEqual(mt["metrics"]["test"]["accuracy"], saved["test"]["accuracy"])
        self.assertIn("confusion_matrix.png", mt["images"]); self.assertIn("feature_importance.png", mt["images"])


if __name__ == "__main__":
    unittest.main()
