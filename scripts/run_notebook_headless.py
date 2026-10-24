"""Execute the notebook's code cells as one script (no Jupyter needed).
Usage: IDS_MODE=smoke IDS_OUT=/tmp/out python scripts/run_notebook_headless.py"""
import json, os, sys
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
nb = json.loads((Path(__file__).resolve().parents[1] / "notebooks" / "smart_home_intrusion_detection.ipynb").read_text())
ns = {"__name__": "__main__", "display": print}
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] == "code":
        exec(compile("".join(c["source"]), f"<cell {i}>", "exec"), ns)
