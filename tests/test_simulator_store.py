import unittest

import tests.conftest_helpers  # noqa: F401  (adds backend/ to sys.path)
from app.services.simulation import SimulationService
from app.services.simulator import CYCLE, Simulator, classify_by_rule
from app.services.store import EventStore


def run(seed, ticks):
    s = Simulator(seed)
    return [e for _ in range(ticks) for e in s.next_tick()]


class SimulatorTests(unittest.TestCase):
    def test_deterministic_for_seed(self):
        key = lambda evs: [(e["device_id"], e["event_type"], e["label"], e["metrics"]) for e in evs]
        self.assertEqual(key(run(7, 25)), key(run(7, 25)))
        self.assertNotEqual(key(run(7, 25)), key(run(8, 25)))

    def test_cycle_contains_every_scenario_and_normal_traffic(self):
        labels = {e["label"] for e in run(42, CYCLE)}
        self.assertEqual(labels, {"normal", "brute_force", "connection_burst", "publish_flood", "topic_enumeration"})

    def test_all_events_marked_simulated_rule_based(self):
        for e in run(1, CYCLE):
            self.assertTrue(e["is_simulated"]); self.assertEqual(e["detection_source"], "simulation_rule")

    def test_rule_thresholds(self):
        self.assertEqual(classify_by_rule("auth_failure", {"failed_auth_60s": 3}), ("brute_force", "medium"))
        self.assertEqual(classify_by_rule("auth_failure", {"failed_auth_60s": 6}), ("brute_force", "high"))
        self.assertEqual(classify_by_rule("publish", {"msgs_per_min": 119}), ("normal", "info"))
        self.assertEqual(classify_by_rule("wildcard_subscribe", {"wildcard_subscribe": True}), ("topic_enumeration", "high"))


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = EventStore(":memory:")
        self.sim = SimulationService(self.store, 42, 1.5)

    def test_lifecycle(self):
        self.assertEqual(self.sim.state, "stopped")
        self.assertEqual(self.sim.start()["state"], "running")
        self.assertEqual(self.sim.pause()["state"], "paused")
        self.assertEqual(self.sim.resume()["state"], "running")
        self.sim.step(CYCLE)
        self.assertGreater(self.store.counts()["total"], 0)
        self.assertEqual(self.sim.reset()["state"], "stopped")
        self.assertEqual(self.store.counts()["total"], 0)

    def test_filters_pagination_and_search(self):
        self.sim.step(CYCLE * 2)
        total, _ = self.store.query(limit=1)
        self.assertEqual(total, self.store.counts()["total"])
        t, items = self.store.query(label="brute_force", limit=50)
        self.assertTrue(items and all(i["label"] == "brute_force" for i in items)); self.assertEqual(t, len(items))
        t, items = self.store.query(q="LOCK", limit=200)
        self.assertTrue(items and all("lock" in (i["device_name"] + i["topic"]).lower() for i in items))
        _, p1 = self.store.query(limit=5, offset=0); _, p2 = self.store.query(limit=5, offset=5)
        self.assertFalse({e["id"] for e in p1} & {e["id"] for e in p2})

    def test_status_update_and_invalid_status(self):
        self.sim.step(CYCLE)
        _, items = self.store.query(label="brute_force", limit=1)
        self.assertEqual(self.store.set_status(items[0]["id"], "resolved")["status"], "resolved")
        with self.assertRaises(ValueError): self.store.set_status(items[0]["id"], "bogus")
        self.assertIsNone(self.store.set_status(99999, "open"))

    def test_device_stats_reflect_alerts(self):
        self.sim.step(CYCLE)
        stats = self.store.device_stats()
        self.assertTrue(any(v["open_alerts"] > 0 for v in stats.values()))


if __name__ == "__main__":
    unittest.main()
