"""Create a SYNTHETIC smoke-test model in ./models and ./reports so ML mode can be exercised locally.
This is a pipeline check, not a benchmark. Delete models/* and reports/* to return to demo mode."""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    env = {**os.environ, "IDS_MODE": "smoke", "IDS_OUT": tmp}
    subprocess.run([sys.executable, str(root / "scripts" / "run_notebook_headless.py")], check=True, env=env)
    for sub in ("models", "reports"):
        (root / sub).mkdir(exist_ok=True)
        for f in Path(tmp, sub).glob("*"):
            shutil.copy(f, root / sub / f.name)
print("Smoke model installed (SYNTHETIC). Restart the backend or POST /api/model/reload.")
