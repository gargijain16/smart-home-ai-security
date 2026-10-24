"""Deterministic smart-home MQTT event simulator.

EVERYTHING produced here is simulated. Labels come from transparent threshold rules (RULES), NOT from the
trained ML model: the simulated events do not carry the dataset's frame-level features, so the model cannot score them.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

DEVICES: List[Dict[str, str]] = [
    {"id": "lock-front", "name": "Front door lock", "type": "Smart lock", "room": "Entrance", "protocol": "MQTT"},
    {"id": "lock-back", "name": "Back door lock", "type": "Smart lock", "room": "Kitchen", "protocol": "MQTT"},
    {"id": "cam-porch", "name": "Porch camera", "type": "Security camera", "room": "Porch", "protocol": "MQTT"},
    {"id": "cam-garage", "name": "Garage camera", "type": "Security camera", "room": "Garage", "protocol": "MQTT"},
    {"id": "motion-hall", "name": "Hallway motion sensor", "type": "Motion sensor", "room": "Hallway", "protocol": "MQTT"},
    {"id": "light-living", "name": "Living room lights", "type": "Smart light", "room": "Living room", "protocol": "MQTT"},
    {"id": "light-bedroom", "name": "Bedroom lights", "type": "Smart light", "room": "Bedroom", "protocol": "MQTT"},
    {"id": "hvac-main", "name": "Main HVAC controller", "type": "HVAC controller", "room": "Utility", "protocol": "MQTT"},
    {"id": "gateway-hub", "name": "IoT gateway", "type": "IoT gateway", "room": "Study", "protocol": "MQTT broker"},
]
_BY_ID = {d["id"]: d for d in DEVICES}
_IP = {d["id"]: f"192.168.1.{10 + i}" for i, d in enumerate(DEVICES)}

RULES: Dict[str, Dict[str, Any]] = {
    "brute_force": {"description": "Repeated failed MQTT authentication", "metric": "failed_auth_60s", "medium_at": 3, "high_at": 6},
    "connection_burst": {"description": "Unusually frequent connections from one client", "metric": "connections_per_min", "medium_at": 20, "high_at": 50},
    "publish_flood": {"description": "Excessive message publishing", "metric": "msgs_per_min", "medium_at": 120, "high_at": 300},
    "topic_enumeration": {"description": "Wildcard subscription from a non-gateway client", "metric": "wildcard_subscribe", "medium_at": None, "high_at": True},
}
LABELS = ["normal"] + list(RULES)

# (scenario, first tick, last tick) inside a repeating 20-tick cycle, and the devices it rotates across.
CYCLE = 20
SCENARIOS: List[Tuple[str, int, int, List[str]]] = [
    ("brute_force", 8, 10, ["lock-front", "lock-back"]),
    ("connection_burst", 14, 15, ["cam-porch", "cam-garage"]),
    ("publish_flood", 17, 18, ["motion-hall", "light-living"]),
    ("topic_enumeration", 19, 19, ["gateway-hub"]),
]


def classify_by_rule(event_type: str, metrics: Dict[str, Any]) -> Tuple[str, str]:
    """Return (label, severity) from the simulation rules."""
    if metrics.get("wildcard_subscribe"):
        return "topic_enumeration", "high"
    for name in ("brute_force", "connection_burst", "publish_flood"):
        r = RULES[name]
        v = metrics.get(r["metric"], 0)
        if v >= r["high_at"]:
            return name, "high"
        if v >= r["medium_at"]:
            return name, "medium"
    return "normal", "info"


class Simulator:
    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)
        self.tick_no = 0

    def _event(self, device_id: str, event_type: str, topic_suffix: str, source_ip: str, **m: Any) -> Dict[str, Any]:
        d = _BY_ID[device_id]
        metrics = {"failed_auth_60s": 0, "msgs_per_min": self.rng.randint(2, 20),
                   "connections_per_min": self.rng.randint(1, 4), "wildcard_subscribe": False,
                   "payload_bytes": self.rng.randint(24, 512)}
        metrics.update(m)
        topic = "#" if metrics["wildcard_subscribe"] else f"home/{d['room'].lower().replace(' ', '-')}/{device_id}/{topic_suffix}"
        label, severity = classify_by_rule(event_type, metrics)
        return {"device_id": device_id, "device_name": d["name"], "event_type": event_type, "protocol": d["protocol"],
                "topic": topic, "source_ip": source_ip, "metrics": metrics, "label": label, "severity": severity,
                "status": "open" if label != "normal" else "resolved", "detection_source": "simulation_rule",
                "is_simulated": True}

    def next_tick(self) -> List[Dict[str, Any]]:
        cycle, pos = divmod(self.tick_no, CYCLE)
        self.tick_no += 1
        events: List[Dict[str, Any]] = []
        for _ in range(2):  # background traffic
            dev = self.rng.choice(DEVICES)["id"]
            kind = self.rng.choices(["heartbeat", "publish", "mqtt_connect"], weights=[5, 4, 1])[0]
            suffix = {"heartbeat": "heartbeat", "publish": "state", "mqtt_connect": "connect"}[kind]
            events.append(self._event(dev, kind, suffix, _IP[dev]))
        attacker_ip = f"192.168.1.{self.rng.randint(150, 250)}"
        for name, start, end, targets in SCENARIOS:
            if not (start <= pos <= end):
                continue
            dev = targets[cycle % len(targets)]
            step = pos - start
            if name == "brute_force":
                events.append(self._event(dev, "auth_failure", "auth", attacker_ip,
                                          failed_auth_60s=3 + step * 3 + self.rng.randint(0, 1)))
            elif name == "connection_burst":
                events.append(self._event(dev, "mqtt_connect", "connect", attacker_ip,
                                          connections_per_min=self.rng.randint(25, 60)))
            elif name == "publish_flood":
                lo, hi = (140, 260) if step == 0 else (310, 420)
                events.append(self._event(dev, "publish", "state", attacker_ip, msgs_per_min=self.rng.randint(lo, hi)))
            else:
                events.append(self._event(dev, "wildcard_subscribe", "subscribe", attacker_ip, wildcard_subscribe=True))
        return events
