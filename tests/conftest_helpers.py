"""Shared helpers: build a SYNTHETIC smoke-test model once per test run by executing the notebook headless."""
import os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
_CACHE = {}


def smoke_artifacts() -> Path:
    if "dir" not in _CACHE:
        tmp = Path(tempfile.mkdtemp(prefix="ids_smoke_"))
        env = {**os.environ, "IDS_MODE": "smoke", "IDS_OUT": str(tmp), "MPLBACKEND": "Agg"}
        subprocess.run([sys.executable, str(ROOT / "scripts" / "run_notebook_headless.py")], check=True, env=env,
                       stdout=subprocess.DEVNULL)
        _CACHE["dir"] = tmp
    return _CACHE["dir"]
