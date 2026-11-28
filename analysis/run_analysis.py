"""Pilot-2 analysis: cleaning -> screening -> planned contrasts -> mixed model -> data quality -> figures and a report.

usage:
  python analysis/run_analysis.py --sheet trials.csv sessions.csv [--out out/] [--version pilot2-0.4]
  python analysis/run_analysis.py --json results/*.json [--out out/]

Everything that decides the result was fixed before data collection (project docs 2026-11-25_pilot2_short_version,
2026-11-27_pilot2_dryrun_power, research proposal H1-H3):
- exclusion criteria A and B (same code as tools/screening.py) and C (eligibility: answered "yes" to the post-question on hearing
  problems; "don't know" is kept, decided 2026-11-28 before any data); the analysis is reported with and without them
- primary inference = one-sample t-tests over listeners on each listener's contrast of mean answers (the test the power
  analysis assumed), effect = mean difference in answer points with 95 % CI and d_z
- families: H1 over Q1-Q3 (Holm); four neighbouring level steps (Bonferroni .05/4); -9 vs -6 equivalence by TOST, +-0.3 points;
  ITDG pairs over 0/20/40 ms (Holm); H2 ITDG x seat as in the power analysis; ITDG x level is exploratory
- linear mixed model (random intercept per listener) with likelihood-ratio tests per term, sum coding: supporting, not primary
Lab (in-person) and online data are analysed separately; lab is the main data set.
"""
import argparse, os, sys
import numpy as np, pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
import load  # noqa: E402

ITEMS = {"q1": "Q1 direction", "q2": "Q2 naturalness", "q3": "Q3 stability"}
LEVELS, ITDGS, SEATS = [-9, -6, -3, 0, 6], [0, 20, 40], ["L", "C", "R"]
N_TRIALS = 64
A_Q2_MAX, A_MIN_FAILS, B_LIMIT = 2, 2, 1.6
TOST_BOUND = 0.3


# ---------------------------------------------------------------- cleaning and screening
def clean(t, s, version):
    log = []
    s = s.copy()
    s["n_trials"] = s["session_id"].map(t.groupby("session_id").size()).fillna(0).astype(int)
    s["finished"] = s["finished_at"].notna() if "finished_at" in s else False
    drop = pd.Series("", index=s.index)
    drop[s["debug"]] = "debug run"
    drop[(drop == "") & s["pid"].fillna("").str.upper().str.contains("TEST")] = "test participant code"
    if version:
        drop[(drop == "") & (s["version"] != version)] = "other site version"
    drop[(drop == "") & ((s["n_trials"] < N_TRIALS) | ~s["finished"])] = "incomplete"
    s["drop_reason"] = drop
    keep = s[drop == ""].sort_values("started_at")
    dup = keep.duplicated("pid", keep="first")          # same participant code twice: keep the first complete session
    s.loc[keep.index[dup], "drop_reason"] = "repeat session of the same participant code"
    for r, n in s["drop_reason"].value_counts().items():
        if r:
            log.append(f"{r}: {n}")
    s_ok = s[s["drop_reason"] == ""]
    t_ok = t[t["session_id"].isin(s_ok["session_id"])].merge(s_ok[["session_id", "pid"]].rename(columns={"pid": "pid_s"}), on="session_id")
    t_ok["pid"] = t_ok["pid_s"]
    return t_ok.drop(columns="pid_s"), s, log


def screen(t, s):
    hearing = s.set_index("pid")["post_hearing_problem"] if "post_hearing_problem" in s else pd.Series(dtype=object)
    rows = []
    for pid, g in t.groupby("pid"):
        hid = g[g["hidden"] == 1]
        a_fails = int((hid["q2"] <= A_Q2_MAX).sum())
        c = g[(g["seat"] == "C") & (g["hidden"] == 0)].pivot_table(index="file", columns="rep", values=["q1", "q2", "q3"])
        diffs = []
        for q in ("q1", "q2", "q3"):
            if (q, 1) in c and (q, 2) in c:
                diffs += list((c[(q, 1)] - c[(q, 2)]).abs().dropna())
        b = float(np.mean(diffs)) if diffs else np.nan
        ex_a = len(hid) > 0 and a_fails >= A_MIN_FAILS
        ex_b = bool(b >= B_LIMIT) if not np.isnan(b) else False
        ex_c = str(hearing.get(pid, "")).lower() == "yes"        # eligibility: reported a hearing problem ("dk" = don't know is kept)
        rows.append(dict(pid=pid, hidden_n=len(hid), A_fails=a_fails, B_mean_abs_diff=round(b, 3), hearing_problem=hearing.get(pid, ""),
                         exclude_A=ex_a, exclude_B=ex_b, exclude_C=ex_c, exclude=ex_a or ex_b or ex_c))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- planned contrasts
def listener_means(t, item):
    d = t[t["hidden"] == 0]
    return {
        "lv": d.pivot_table(index="pid", columns="level_ratio_db", values=item),
        "it": d.pivot_table(index="pid", columns="itdg_ms", values=item),
        "side_it": d[d["seat"].isin(["L", "R"])].pivot_table(index="pid", columns="itdg_ms", values=item),
        "cen_it": d[d["seat"] == "C"].pivot_table(index="pid", columns="itdg_ms", values=item),
        "hi_it": d[d["level_ratio_db"].isin([0, 6])].pivot_table(index="pid", columns="itdg_ms", values=item),
        "lo_it": d[d["level_ratio_db"].isin([-9, -6])].pivot_table(index="pid", columns="itdg_ms", values=item),
    }


def contrast_values(m):
    lv, it = m["lv"], m["it"]
    return {
        "H1: mean(-6,-3) vs +6 dB": (lv[-6] + lv[-3]) / 2 - lv[6],
        "-9 vs -6 dB (equivalence)": lv[-9] - lv[-6],
        "-6 vs -3 dB": lv[-6] - lv[-3],
        "-3 vs 0 dB": lv[-3] - lv[0],
        "0 vs +6 dB": lv[0] - lv[6],
        "ITDG 0 vs 20 ms": it[0] - it[20],
        "ITDG 0 vs 40 ms": it[0] - it[40],
        "ITDG 20 vs 40 ms": it[20] - it[40],
        "H2: ITDG x seat (20-0 ms, side - centre)": (m["side_it"][20] - m["side_it"][0]) - (m["cen_it"][20] - m["cen_it"][0]),
        "H2 (secondary): side seats, 20 vs mean(0,40) ms": m["side_it"][20] - (m["side_it"][0] + m["side_it"][40]) / 2,
        "Exploratory: ITDG x level (40-0 ms, 0/+6 - -9/-6 dB)": (m["hi_it"][40] - m["hi_it"][0]) - (m["lo_it"][40] - m["lo_it"][0]),
    }


FAMILY = {"H1: mean(-6,-3) vs +6 dB": "H1", "-6 vs -3 dB": "steps", "-3 vs 0 dB": "steps", "0 vs +6 dB": "steps",
          "ITDG 0 vs 20 ms": "itdg", "ITDG 0 vs 40 ms": "itdg", "ITDG 20 vs 40 ms": "itdg"}


def holm(p):
    p = np.asarray(p, float); o = np.argsort(p); adj = np.empty_like(p); run = 0
    for k, i in enumerate(o):
        run = max(run, min(1, (len(p) - k) * p[i])); adj[i] = run
    return adj


def test_contrasts(t):
    rows = []
    for item in ITEMS:
        for name, v in contrast_values(listener_means(t, item)).items():
            v = v.dropna(); n = len(v); mean = v.mean(); sd = v.std(ddof=1); se = sd / np.sqrt(n)
            tc = stats.t.ppf(0.975, n - 1)
            r = dict(item=item, contrast=name, n=n, mean_diff=mean, ci_low=mean - tc * se, ci_high=mean + tc * se, d_z=mean / sd if sd > 0 else np.nan)
            if "equivalence" in name:
                t90 = stats.t.ppf(0.95, n - 1)
                p_lo = stats.t.sf((mean + TOST_BOUND) / se, n - 1); p_hi = stats.t.cdf((mean - TOST_BOUND) / se, n - 1)
                r.update(p=max(p_lo, p_hi), test=f"TOST +-{TOST_BOUND}", ci90_low=mean - t90 * se, ci90_high=mean + t90 * se)
            else:
                r.update(p=stats.ttest_1samp(v, 0).pvalue, test="t")
            rows.append(r)
    df = pd.DataFrame(rows)
    df["p_adj"] = df["p"]; df["adjust"] = "none"
    h1 = df["contrast"].str.startswith("H1:")
    df.loc[h1, "p_adj"] = holm(df.loc[h1, "p"]); df.loc[h1, "adjust"] = "Holm over Q1-Q3"
    st = df["contrast"].map(FAMILY) == "steps"
    df.loc[st, "p_adj"] = np.minimum(1, df.loc[st, "p"] * 4); df.loc[st, "adjust"] = "Bonferroni x4 (level steps)"
    for item in ITEMS:
        m = (df["item"] == item) & (df["contrast"].map(FAMILY) == "itdg")
        df.loc[m, "p_adj"] = holm(df.loc[m, "p"]); df.loc[m, "adjust"] = "Holm over ITDG pairs"
    df.loc[df["contrast"].str.startswith("Exploratory"), "adjust"] = "exploratory"
    return df


# ---------------------------------------------------------------- mixed model
def _sum_cols(x, levels, name):
    cols = {}
    for k in levels[:-1]:
        cols[f"{name}[{k}]"] = (x == k).astype(float) - (x == levels[-1]).astype(float)
    return pd.DataFrame(cols)


def lmm(t, item):
    import statsmodels.api as sm
    d = t[t["hidden"] == 0].dropna(subset=[item]).reset_index(drop=True)
    f = {"level": _sum_cols(d["level_ratio_db"], LEVELS, "lv"), "itdg": _sum_cols(d["itdg_ms"], ITDGS, "it"), "seat": _sum_cols(d["seat"], SEATS, "st")}
    terms = dict(f)
    for a, b in (("level", "itdg"), ("level", "seat"), ("itdg", "seat")):
        terms[f"{a} x {b}"] = pd.DataFrame({f"{x}:{y}": f[a][x] * f[b][y] for x in f[a] for y in f[b]})
    terms["level x itdg x seat"] = pd.DataFrame({f"{x}:{y}:{z}": f["level"][x] * f["itdg"][y] * f["seat"][z] for x in f["level"] for y in f["itdg"] for z in f["seat"]})

    def fit(names):
        X = pd.concat([pd.Series(1.0, index=d.index, name="const")] + [terms[n] for n in names], axis=1)
        return sm.MixedLM(d[item].astype(float), X, groups=d["pid"]).fit(reml=False)
    full_names = list(terms)
    full = fit(full_names)
    rows = []
    for n in full_names:
        red = fit([m for m in full_names if m != n])
        lr = 2 * (full.llf - red.llf); df_ = terms[n].shape[1]
        rows.append(dict(item=item, term=n, df=df_, LR=lr, p=stats.chi2.sf(max(lr, 0), df_)))
    var_subj = float(full.cov_re.iloc[0, 0]); var_res = float(full.scale)
    return pd.DataFrame(rows), dict(item=item, listener_sd=np.sqrt(var_subj), residual_sd=np.sqrt(var_res), n_obs=len(d), converged=bool(full.converged))


# ---------------------------------------------------------------- data quality
def quality(t, s):
    q = {}
    hid = t[t["hidden"] == 1]
    q["hidden"] = hid.groupby("seat")[["q1", "q2", "q3"]].mean().round(2)
    q["q1_hard_rate"] = t.groupby("pid")["q1_hard"].mean().describe().round(3)
    c = t[(t["seat"] == "C") & (t["hidden"] == 0)]
    rr = []
    for pid, g in c.groupby("pid"):
        p = g.pivot_table(index="file", columns="rep", values=["q1", "q2", "q3"])
        for it in ITEMS:
            if (it, 1) in p and (it, 2) in p:
                a, b = p[(it, 1)], p[(it, 2)]
                rho = stats.spearmanr(a, b).statistic if a.nunique() > 1 and b.nunique() > 1 else np.nan
                rr.append(dict(pid=pid, item=it, mean_abs_diff=(a - b).abs().mean(), spearman=rho))
    rr = pd.DataFrame(rr)
    q["retest"] = rr.groupby("item")[["mean_abs_diff", "spearman"]].median().round(3) if len(rr) else pd.DataFrame()
    sep = []
    for pid, g in t[t["hidden"] == 0].groupby("pid"):
        for a, b in (("q1", "q3"), ("q1", "q2"), ("q2", "q3")):
            if g[a].nunique() > 1 and g[b].nunique() > 1:
                sep.append(dict(pair=f"{a}-{b}", r=stats.spearmanr(g[a], g[b]).statistic))
    q["separability"] = pd.DataFrame(sep).groupby("pair")["r"].describe()[["count", "25%", "50%", "75%"]].round(2) if sep else pd.DataFrame()
    # from consent, not from page start: a session can be opened (language chosen) long before the participant arrives and then resumed
    t0 = s["consent_at"].fillna(s["started_at"]) if "consent_at" in s else s["started_at"]
    dur = (s["finished_at"] - t0).dt.total_seconds() / 60 if "finished_at" in s else pd.Series(dtype=float)
    q["duration_min"] = dur.describe().round(1)
    q["listen_s"] = t["listen_s"].describe().round(2)
    q["quiz_attempts"] = s["quiz_attempts"].value_counts().sort_index() if "quiz_attempts" in s else pd.Series(dtype=int)
    for col in ("post_hearing_problem", "post_fatigue", "post_q1q3_difficult"):
        if col in s:
            q[col] = s[col].value_counts(dropna=False).sort_index()
    if "post_experience_years" in s:
        q["post_experience_years"] = pd.to_numeric(s["post_experience_years"], errors="coerce").describe().round(1)
    if "volume_system" in s:
        vs = pd.to_numeric(s["volume_system"], errors="coerce"); ve = pd.to_numeric(s.get("volume_system_end"), errors="coerce")
        q["volume_mac"] = pd.Series({"n": int(vs.notna().sum()), "min": vs.min(), "median": vs.median(), "max": vs.max(), "changed_during_session": int(((ve - vs).abs() > 0).sum())})
    return q


# ---------------------------------------------------------------- figures
INK, INK2, GRID, BASE, SURF = "#191919", "#666666", "#e8e8e8", "#c2c2c2", "#ffffff"
SERIES = {0: "#257de0", 20: "#f47230", 40: "#00b894"}            # validated 3-slot categorical set (dataviz reference palette)


def _style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(BASE)
    ax.tick_params(colors=INK2, labelsize=8, length=0)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)


def fig_means(t, path, title):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    d = t[t["hidden"] == 0]
    pm = d.groupby(["pid", "seat", "itdg_ms", "level_ratio_db"])[list(ITEMS)].mean().reset_index()
    fig, axes = plt.subplots(3, 3, figsize=(10.5, 8.6), sharex=True, sharey=True, facecolor=SURF)
    off = {0: -0.45, 20: 0, 40: 0.45}
    for i, item in enumerate(ITEMS):
        for j, seat in enumerate(SEATS):
            ax = axes[i, j]; _style(ax)
            g = pm[pm["seat"] == seat]; ends = []
            for it in ITDGS:
                h = g[g["itdg_ms"] == it].groupby("level_ratio_db")[item]
                mu, se, n = h.mean(), h.std(ddof=1) / np.sqrt(h.count()), h.count()
                ci = se * stats.t.ppf(0.975, n - 1)
                x = np.array(mu.index, float) + off[it]
                ax.plot(x, mu.values, color=SERIES[it], lw=2, zorder=3)
                ax.errorbar(x, mu.values, yerr=ci.values, fmt="none", ecolor=SERIES[it], elinewidth=1.4, capsize=0, zorder=3)
                ax.scatter(x, mu.values, s=42, color=SERIES[it], edgecolor=SURF, linewidth=1.5, zorder=4)
                if i == 0 and j == 2:
                    ends.append([mu.values[-1], it, x[-1]])
            if ends:                                   # direct labels at the line ends, pushed apart so they never overlap
                ends.sort(); gap = 0.28
                for k in range(1, len(ends)):
                    ends[k][0] = max(ends[k][0], ends[k - 1][0] + gap)
                for yy, it, xx in ends:
                    ax.annotate(f"{it} ms", (7.0, yy), xytext=(0, 0), textcoords="offset points", va="center", fontsize=8, color=INK, annotation_clip=False)
            ax.set_xlim(-10.2, 6.9 if not (i == 0 and j == 2) else 6.9)
            ax.set_ylim(0.8, 5.2); ax.set_yticks([1, 2, 3, 4, 5]); ax.set_xticks(LEVELS); ax.set_xticklabels(["−9", "−6", "−3", "0", "+6"])
            if i == 0:
                ax.set_title({"L": "Left seat", "C": "Centre seat", "R": "Right seat"}[seat], fontsize=10, color=INK, loc="left")
            if j == 0:
                ax.set_ylabel(ITEMS[item] + "\n(1–5, mean ± 95% CI)", fontsize=9, color=INK2)
            if i == 2:
                ax.set_xlabel("PA level re. direct sound (dB)", fontsize=9, color=INK2)
    handles = [plt.Line2D([], [], color=SERIES[it], lw=2, marker="o", ms=6, mec=SURF, label=f"ITDG {it} ms") for it in ITDGS]
    fig.legend(handles=handles, loc="upper right", ncol=3, frameon=False, fontsize=9, bbox_to_anchor=(0.98, 0.995))
    fig.suptitle(title, x=0.02, ha="left", fontsize=12, color=INK)
    fig.text(0.02, 0.005, "Points: mean of listener means; whiskers: 95% CI across listeners. Hidden references excluded. Points offset by ITDG for legibility.", fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.02, 1, 0.96)); fig.savefig(path, dpi=160); fig.savefig(path.replace(".png", ".svg")); plt.close(fig)


def fig_contrasts(df, path, title):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    names = list(dict.fromkeys(df["contrast"]))
    fig, axes = plt.subplots(1, 3, figsize=(12, 5.4), sharey=True, sharex=True, facecolor=SURF)
    y = np.arange(len(names))[::-1]
    for k, item in enumerate(ITEMS):
        ax = axes[k]; _style(ax); ax.grid(axis="x", color=GRID, lw=0.8); ax.grid(axis="y", visible=False)
        g = df[df["item"] == item].set_index("contrast").loc[names]
        ax.axvline(0, color=BASE, lw=1)
        eq = names.index("-9 vs -6 dB (equivalence)")
        ax.plot([-TOST_BOUND, TOST_BOUND], [y[eq], y[eq]], color=GRID, lw=9, solid_capstyle="butt", zorder=1)
        lo = g["ci_low"].copy(); hi = g["ci_high"].copy()
        lo.iloc[eq] = g["ci90_low"].iloc[eq]; hi.iloc[eq] = g["ci90_high"].iloc[eq]          # TOST decides on the 90% CI
        ax.hlines(y, lo, hi, color="#257de0", lw=1.6, zorder=2)
        for name_ in ("-9 vs -6 dB (equivalence)", "ITDG 0 vs 20 ms", "H2: ITDG x seat (20-0 ms, side - centre)", "Exploratory: ITDG x level (40-0 ms, 0/+6 - -9/-6 dB)"):
            ax.axhline(y[names.index(name_)] + 0.5, color=GRID, lw=0.8, zorder=0)
        ax.scatter(g["mean_diff"], y, s=42, color="#257de0", edgecolor=SURF, linewidth=1.5, zorder=3)
        ax.set_title(ITEMS[item], fontsize=10, color=INK, loc="left")
        ax.set_xlabel("difference in answer points", fontsize=8.5, color=INK2)
    axes[0].set_yticks(y); axes[0].set_yticklabels(names, fontsize=8, color=INK)
    fig.suptitle(title, x=0.02, ha="left", fontsize=12, color=INK)
    fig.text(0.02, 0.01, f"Each listener's contrast of mean answers; positive = the first-named condition rated higher. −9 vs −6 row: 90% CI against the equivalence bounds ±{TOST_BOUND} (grey band); other rows: 95% CI.", fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95)); fig.savefig(path, dpi=160); fig.savefig(path.replace(".png", ".svg")); plt.close(fig)


# ---------------------------------------------------------------- report
def md_table(df, floatfmt=3):
    df = df.copy()
    for c in df.columns:
        if df[c].dtype.kind == "f":
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else (str(int(v)) if float(v).is_integer() and abs(v) < 1e6 else (f"{v:.{floatfmt}f}" if abs(v) >= 0.001 else f"{v:.1e}")))
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(str(v) for v in r) + " |" for r in df.astype(str).values]
    return "\n".join(out)


def pstr(p):
    return "< .001" if p < 0.001 else f"{p:.3f}"


def analyse_set(t, label, out, tag):
    res = test_contrasts(t)
    res.to_csv(os.path.join(out, f"contrasts_{tag}.csv"), index=False)
    lm_rows, lm_info = [], []
    for item in ITEMS:
        a, b = lmm(t, item); lm_rows.append(a); lm_info.append(b)
    lm = pd.concat(lm_rows); lm.to_csv(os.path.join(out, f"lmm_lrt_{tag}.csv"), index=False)
    return res, lm, pd.DataFrame(lm_info)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sheet", nargs=2, metavar=("TRIALS_CSV", "SESSIONS_CSV"))
    g.add_argument("--json", nargs="+")
    ap.add_argument("--out", default="analysis_out")
    ap.add_argument("--version", default="pilot2-0.4", help="site version to analyse ('' = all)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t, s = load.from_sheet(*a.sheet) if a.sheet else load.from_json(a.json)
    simulated = bool(s["simulated"].any())
    t_ok, s_all, log = clean(t, s, a.version)
    s_all.to_csv(os.path.join(a.out, "sessions_all.csv"), index=False)
    for mode in ("lab", "online"):
        tm = t_ok[t_ok["mode"] == mode]
        if tm["pid"].nunique() < 3:
            continue
        sm_ = s_all[(s_all["mode"] == mode) & (s_all["drop_reason"] == "")]
        scr = screen(tm, sm_); scr.to_csv(os.path.join(a.out, f"screening_{mode}.csv"), index=False)
        kept = scr.loc[~scr["exclude"], "pid"]
        t_main = tm[tm["pid"].isin(kept)]
        res, lm, info = analyse_set(t_main, "after exclusions", a.out, f"{mode}_main")
        res_all, lm_all, _ = analyse_set(tm, "all listeners", a.out, f"{mode}_all")
        fig_means(t_main, os.path.join(a.out, f"fig_means_{mode}.png"), f"Pilot 2, {mode}: mean answers by seat, level ratio and ITDG (n = {t_main['pid'].nunique()})")
        fig_contrasts(res, os.path.join(a.out, f"fig_contrasts_{mode}.png"), f"Pilot 2, {mode}: planned contrasts (n = {t_main['pid'].nunique()})")
        q = quality(tm, sm_)
        write_report(a.out, mode, simulated, log, s_all, scr, res, res_all, lm, lm_all, info, q, t_main)
    print("done ->", a.out)


def write_report(out, mode, simulated, log, s_all, scr, res, res_all, lm, lm_all, info, q, t_main):
    L = []
    L.append(f"# 2차 파일럿 분석 결과 — {'대면(lab)' if mode == 'lab' else '온라인(online)'}")
    if simulated:
        L.append("\n> **모의 데이터입니다.** `analysis/simulate.py`가 가정한 효과로 만든 시험용 값이며 지각 결과가 아닙니다. 분석 코드가 제대로 도는지 확인하는 용도입니다.")
    L.append("\n생성: `analysis/run_analysis.py`. 대면과 온라인은 따로 분석한다(대면 = 주 데이터).")
    L.append("\n## 1. 데이터와 제외")
    n_ses = len(s_all[s_all["mode"] == mode]); n_ok = scr.shape[0]; n_ex = int(scr["exclude"].sum())
    L.append(f"- 수신 세션 {n_ses}개 → 분석 대상 완료 세션 {n_ok}명. 정리 사유(전체 모드): " + ("; ".join(log) if log else "없음"))
    L.append(f"- 사전 확정 제외 기준: A(숨은 기준음 4개 중 2개 이상 Q2 ≤ 2) {int(scr['exclude_A'].sum())}명, B(C석 재검사 평균 절대차 ≥ 1.6) {int(scr['exclude_B'].sum())}명, C(참여 조건: 사후 질문에서 청각 이상 \"있음\") {int(scr['exclude_C'].sum())}명, 합계 {n_ex}명(중복 제외) → **주 분석 {n_ok - n_ex}명**.")
    L.append("- 전체 표본(제외 전) 결과는 4절 민감도 분석에 함께 제시한다.")
    L.append("\n## 2. 계획된 대비 (주 분석)")
    L.append("참가자마다 조건 평균의 차이를 구하고 참가자들에 걸쳐 단일표본 t검정. 효과 = 응답 점수 차(1–5 척도), 95% CI, d_z. 양수 = 앞에 적은 조건이 더 높게 평가됨.")
    show = res.copy()
    show["result"] = [pstr(p) for p in show["p_adj"]]
    show = show[["item", "contrast", "n", "mean_diff", "ci_low", "ci_high", "d_z", "p", "result", "adjust"]].rename(columns={"result": "p_adj"})
    show["p"] = show["p"].map(pstr)
    for item, name in ITEMS.items():
        L.append(f"\n### {name}\n")
        L.append(md_table(show[show["item"] == item].drop(columns="item"), 2))
    eq = res[res["contrast"].str.contains("equivalence")]
    L.append("\n−9 vs −6 dB 동등성(TOST, ±0.3점): " + "; ".join(f"{ITEMS[r.item]} 90% CI [{r.ci90_low:.2f}, {r.ci90_high:.2f}], p = {pstr(r.p)}" for r in eq.itertuples()))
    L.append("\n![contrasts](fig_contrasts_%s.png)" % mode)
    L.append("\n## 3. 조건별 평균")
    L.append("![means](fig_means_%s.png)")
    L[-1] = L[-1] % mode
    tab = t_main[t_main["hidden"] == 0].groupby(["seat", "itdg_ms", "level_ratio_db"])[list(ITEMS)].mean().round(2).reset_index()
    L.append("\n<details><summary>표로 보기 (좌석 × ITDG × 레벨비, 응답 평균)</summary>\n\n" + md_table(tab, 2) + "\n\n</details>")
    L.append("\n## 4. 민감도 분석: 제외 전 전체 표본")
    cmp_ = res[["item", "contrast", "mean_diff", "p_adj"]].merge(res_all[["item", "contrast", "mean_diff", "p_adj"]], on=["item", "contrast"], suffixes=("_main", "_all"))
    cmp_["p_adj_main"] = cmp_["p_adj_main"].map(pstr); cmp_["p_adj_all"] = cmp_["p_adj_all"].map(pstr)
    L.append(md_table(cmp_, 2))
    L.append("\n## 5. 선형혼합모형 (보조)")
    L.append("응답 ~ 레벨비 × ITDG × 좌석(합 부호화) + 참가자 무작위 절편, 최대우도. 각 항을 빼고 우도비 검정(유형 III). 응답은 5단계 순서형이라 근사 분석이며, 주 추론은 2절의 대비다.")
    lmx = lm.copy(); lmx["p"] = lmx["p"].map(pstr)
    L.append(md_table(lmx, 2))
    L.append("\n" + md_table(info, 3))
    L.append("\n## 6. 데이터 품질")
    for k, v in q.items():
        if isinstance(v, (pd.DataFrame, pd.Series)) and len(v):
            L.append(f"\n**{k}**\n\n" + md_table(v.reset_index() if isinstance(v, pd.Series) else v.reset_index(), 3))
    L.append("\n- `post_hearing_problem` = yes는 기준 C로 주 분석에서 제외했다(2026-11-28, 데이터 수집 전 결정). \"모르겠다\"는 참여 조건 위반이 아니므로 포함했다.")
    L.append("- retest: C석 1·2회차 15조건의 평균 절대차와 Spearman 상관(참가자별 값의 중앙값). separability: 참가자 안에서 문항 간 Spearman 상관(높을수록 두 문항을 구분하지 못했다는 뜻).")
    L.append("\n## 7. 해석할 때 주의")
    L.append("- 결과는 BRAS CR3 시뮬레이션 BRIR, 한 곡(모차르트 아리아), 가정한 PA 위치, 범용 HRTF(KU100) 조건의 헤드폰 청취에 한정된다. 실제 홀 PA 조건에서 검증된 결과가 아니다.")
    L.append("- 측면석은 조건당 참가자 1응답이라 좌석 관련 효과의 정밀도는 참가자 수에 달려 있다.")
    L.append("- 레벨비 효과에는 전체 음량 변화가 섞여 있다(직접음 고정, PA만 조절한 설계).")
    open(os.path.join(out, f"report_{mode}.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
