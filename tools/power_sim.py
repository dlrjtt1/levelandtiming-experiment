"""How many participants? Monte Carlo power for the pilot-2 design (ITDG 0/20/40 x level -9/-6/-3/0/+6 x seat L/C/R, centre seat twice,
5-point answers), for the contrasts of interest. usage: python tools/power_sim.py [n_sim]

Assumed effect sizes are in units of the residual SD of one answer (sigma). Starting point = pilot 1, Q1 (12 listeners, 3-point scale):
  residual variance 0.374 (from F(level) = 31.17, level means 2.50 / 2.05 / 1.86, 108 answers per level)  -> sigma = 0.61
  level -6 vs +6: 0.64 points = 1.05 sigma; -6 vs 0: 0.45 = 0.74 sigma (0.37 per 3 dB); 0 vs +6: 0.19 = 0.31 sigma
  ITDG 0 vs 40 ms: 0.23 points = 0.38 sigma; 0 vs 20 ms: about 0
  between-listener SD about 0.43 = 0.7 sigma
Pilot 1 used another hall, another scale, other question wording and loudness-normalised stimuli, and 12 listeners give noisy effect
sizes, so the scenario "half" (all effects halved) is run as well. Not from data: listener-specific slopes (SD 0.3 sigma for level,
0.2 for ITDG), the ITDG x seat and ITDG x level interaction sizes, and the -9 vs -6 step.
Test: one-sample t-test over listeners on each listener's contrast of mean answers (two-sided, alpha .05; Holm-type adjusted alpha
where several contrasts form one family). A mixed model on the same data is expected to give similar or slightly higher power."""
import sys, numpy as np
from scipy import stats
rng = np.random.default_rng(1); NSIM = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
ITDG, LV, CELLS = [0, 20, 40], [-9, -6, -3, 0, 6], ["L", "C1", "C2", "R"]          # C1, C2 = the two repetitions at the centre seat

def simulate(n, k=1.0, plateau=True):
    lv_mu = np.array([0.0 if plateau else 0.37, 0.0, -0.37, -0.74, -1.05]) * k        # relative to -6 dB
    it_mu = np.array([0.0, 0.0, -0.38]) * k
    side_it = np.array([-0.2, 0.2, 0.0]) * k        # ITDG x seat: at the side seats 20 ms is 0.4 sigma better relative to 0 ms than at the centre
    inter = np.zeros((3, 5)); inter[2, 3:] = -0.30 * k   # ITDG x level: 40 ms costs 0.3 sigma more at 0 and +6 dB
    y = np.zeros((n, 3, 5, 4))
    subj = rng.normal(0, 0.7, n); s_lv = rng.normal(0, 0.3, n); s_it = rng.normal(0, 0.2, n)
    for c, cell in enumerate(CELLS):
        side = cell in ("L", "R")
        mu = 0.9 + lv_mu[None, :] + it_mu[:, None] + inter + (side_it[:, None] if side else 0) + (-0.2 * k if side else 0)
        lat = mu[None] + subj[:, None, None] + s_lv[:, None, None] * (np.arange(5) - 2)[None, None, :] / 2 + s_it[:, None, None] * (np.arange(3) - 1)[None, :, None] + rng.normal(0, 1, (n, 3, 5))
        y[..., c] = np.clip(np.round(lat * 1.0 + 3), 1, 5)                               # 5-point answer, category width = 1 sigma
    return y

def contrasts(y):
    m_lv = y.mean(axis=(1, 3)); m_it = y.mean(axis=(2, 3))
    side = y[..., [0, 3]].mean(axis=(2, 3)); cen = y[..., [1, 2]].mean(axis=(2, 3))
    hi = y[:, :, 3:, :].mean(axis=(2, 3)); lo = y[:, :, :2, :].mean(axis=(2, 3))
    return {"level -6 vs +6": m_lv[:, 1] - m_lv[:, 4], "level -6 vs -3 (one 3 dB step)": m_lv[:, 1] - m_lv[:, 2], "level -3 vs 0 (one 3 dB step)": m_lv[:, 2] - m_lv[:, 3],
            "ITDG 0 vs 40 ms": m_it[:, 0] - m_it[:, 2], "ITDG x seat (20 vs 0 ms, side vs centre)": (side[:, 1] - side[:, 0]) - (cen[:, 1] - cen[:, 0]),
            "ITDG x level (40 vs 0 ms, 0/+6 vs -9/-6 dB)": (hi[:, 0] - hi[:, 2]) - (lo[:, 0] - lo[:, 2]), "_plateau": m_lv[:, 0] - m_lv[:, 1]}
ALPHA = {"level -6 vs -3 (one 3 dB step)": 0.05 / 4, "level -3 vs 0 (one 3 dB step)": 0.05 / 4}       # four neighbouring level steps = one family

for k, label in ((1.0, "effects as in pilot 1"), (0.5, "effects half as large")):
    print("\n" + label); res = {}
    for n in (6, 12, 18, 24, 30, 36, 48, 60):
        hit = {}
        for _ in range(NSIM):
            c = contrasts(simulate(n, k))
            for name, v in c.items():
                if name == "_plateau":      # equivalence (TOST): is -9 vs -6 within +-0.3 answer points? true difference 0
                    se = v.std(ddof=1) / np.sqrt(n); tcrit = stats.t.ppf(0.95, n - 1); ok = (v.mean() - 0.3) / se < -tcrit and (v.mean() + 0.3) / se > tcrit
                    hit["-9 vs -6 equal within 0.3 points (TOST)"] = hit.get("-9 vs -6 equal within 0.3 points (TOST)", 0) + ok
                else:
                    p = stats.ttest_1samp(v, 0).pvalue; hit[name] = hit.get(name, 0) + (p < ALPHA.get(name, 0.05))
        res[n] = {a: b / NSIM for a, b in hit.items()}
    names = list(res[6]); print("%-46s" % "N" + "".join("%6d" % n for n in res))
    for a in names: print("%-46s" % a + "".join("%6.2f" % res[n][a] for n in res))
