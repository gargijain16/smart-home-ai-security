"""Simulation lifecycle (stopped/running/paused) on top of Simulator + EventStore."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from .simulator import RULES, Simulator
from .store import EventStore

NOTICE = ("All events are simulated. Labels are threshold rules defined in the simulator, "
          "not predictions from the trained model.")


class SimulationService:
    def __init__(self, store: EventStore, seed: int, tick_seconds: float):
        self.store, self.tick_seconds = store, tick_seconds
        self.default_seed = seed
        self.state = "stopped"
        self.run_id = None
        self.events_generated = 0
        self.sim = Simulator(seed)

    def snapshot(self) -> Dict[str, Any]:
        return {"state": self.state, "run_id": self.run_id, "seed": self.sim.seed, "ticks": self.sim.tick_no,
                "events_generated": self.events_generated, "tick_seconds": self.tick_seconds,
                "rules": RULES, "notice": NOTICE}

    def start(self, seed=None) -> Dict[str, Any]:
        if self.state == "paused" and seed is None:
            self.state = "running"
        else:
            self.sim = Simulator(self.default_seed if seed is None else seed)
            self.run_id = f"sim-{uuid.uuid4().hex[:8]}"
            self.events_generated = 0
            self.state = "running"
        return self.snapshot()

    def pause(self) -> Dict[str, Any]:
        if self.state == "running":
            self.state = "paused"
        return self.snapshot()

    def resume(self) -> Dict[str, Any]:
        if self.state == "paused":
            self.state = "running"
        return self.snapshot()

    def reset(self) -> Dict[str, Any]:
        self.store.reset()
        self.sim = Simulator(self.default_seed)
        self.state, self.run_id, self.events_generated = "stopped", None, 0
        return self.snapshot()

    def step(self, ticks: int = 1) -> int:
        """Generate `ticks` ticks of events and persist them. Works in any state (used by tests and demos)."""
        if self.run_id is None:
            self.run_id = f"sim-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        batch = []
        for i in range(ticks):
            stamp = (now + timedelta(milliseconds=i)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            for ev in self.sim.next_tick():
                ev.update(ts=stamp, run_id=self.run_id)
                batch.append(ev)
        self.store.insert_many(batch)
        self.events_generated += len(batch)
        return len(batch)
