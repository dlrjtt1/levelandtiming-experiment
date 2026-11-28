"""Check analysis/clmm.py against R ordinal::clmm on the full analysis model (needs R with the 'ordinal' package).

usage: python analysis/check_clmm.py trials.csv sessions.csv [item]      (item = q1 | q2 | q3, default q2)
Fits answer ~ level x ITDG x seat (sum coding) + (1 | listener) in both, and the model without the seat main effect,
and prints log-likelihoods, listener SD and the likelihood-ratio statistic side by side.
"""
import os, subprocess, sys, tempfile
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import load, run_analysis as ra  # noqa: E402
from clmm import CLMM  # noqa: E402

trials, sessions = sys.argv[1], sys.argv[2]
item = sys.argv[3] if len(sys.argv) > 3 else "q2"
t, s = load.from_sheet(trials, sessions)
t, s_all, _ = ra.clean(t, s, "pilot2-0.4")
t = t[(t["mode"] == "lab") & (t["hidden"] == 0)].dropna(subset=[item]).reset_index(drop=True)
terms = ra._terms(t)
X_full = pd.concat(list(terms.values()), axis=1)
X_red = pd.concat([v for k, v in terms.items() if k != "seat"], axis=1)

py = {}
for name, X in (("full", X_full), ("no_seat", X_red)):
    m = CLMM(t[item].astype(int).to_numpy(), X.to_numpy(), t["pid"].to_numpy()).fit()
    py[name] = (m.llf, m.sigma)

d = tempfile.mkdtemp()
X_full.columns = [f"x{i}" for i in range(X_full.shape[1])]
seat_cols = [f"x{i}" for i, c in enumerate(pd.concat(list(terms.values()), axis=1).columns) if c.startswith("st[")]
out = pd.concat([t[[item, "pid"]].rename(columns={item: "y"}), X_full], axis=1)
out.to_csv(os.path.join(d, "x.csv"), index=False)
xs = " + ".join(X_full.columns); xr = " + ".join(c for c in X_full.columns if c not in seat_cols)
r = f'''suppressMessages(library(ordinal)); d <- read.csv("{d}/x.csv"); d$y <- factor(d$y, ordered = TRUE); d$pid <- factor(d$pid)
f1 <- clmm(y ~ {xs} + (1|pid), data = d, nAGQ = 25); f0 <- clmm(y ~ {xr} + (1|pid), data = d, nAGQ = 25)
cat(as.numeric(logLik(f1)), sqrt(VarCorr(f1)$pid[1]), as.numeric(logLik(f0)), sqrt(VarCorr(f0)$pid[1]), "\\n")'''
o = subprocess.run(["Rscript", "-e", r], capture_output=True, text=True)
if o.returncode:
    sys.exit("R failed: " + o.stderr[-500:])
v = [float(x) for x in o.stdout.split()]
print(f"item {item}, n = {len(t)} answers, {t['pid'].nunique()} listeners")
print(f"            python clmm.py        R ordinal::clmm")
print(f"logLik full  {py['full'][0]:14.4f}   {v[0]:14.4f}")
print(f"SD full      {py['full'][1]:14.4f}   {v[1]:14.4f}")
print(f"logLik -seat {py['no_seat'][0]:14.4f}   {v[2]:14.4f}")
print(f"LR seat      {2 * (py['full'][0] - py['no_seat'][0]):14.4f}   {2 * (v[0] - v[2]):14.4f}")
