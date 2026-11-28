"""Make SIMULATED data in the Google Sheet export format, to test analysis/run_analysis.py end to end.
The answers come from an assumed model (effect sizes of tools/power_sim.py, from pilot 1 Q1); they are not perceptual results.

usage: python analysis/simulate.py [--lab 30] [--online 8] [--out sim/]   -> sim/trials.csv, sim/sessions.csv

Also planted, to test the cleaning and screening: one debug session, one TEST participant, one unfinished session,
re-sent duplicate trials, and two random responders (one of them should be caught by criterion A or B).
"""
import argparse, json, os
from datetime import datetime, timedelta, timezone
import numpy as np, pandas as pd

LEVELS, ITDGS, ORDERS = [-9, -6, -3, 0, 6], [0, 20, 40], ["LCR", "LRC", "CLR", "CRL", "RLC", "RCL"]
LV_MU = np.array([0.0, 0.0, -0.37, -0.74, -1.05])      # relative to -6 dB, in units of the residual SD
IT_MU = np.array([0.0, 0.0, -0.38])
SIDE_IT = np.array([-0.2, 0.2, 0.0])                    # ITDG x seat: at the side seats 20 ms is relatively better
ITEM_K = {"q1": 1.0, "q2": 0.8, "q3": 0.9}              # the three items share the pattern with different strengths


def lv_name(v):
    return f"+{v}" if v > 0 else str(v)


def trials_for(order, rng):
    out = []
    for b, seat in enumerate(order, 1):
        reps = [1, 2] if seat == "C" else [1]
        n = 0
        for rep in reps:
            cond = [(it, lv) for it in ITDGS for lv in LEVELS]
            rng.shuffle(cond)
            items = [dict(seat=seat, rep=rep, itdg_ms=it, level_ratio_db=lv, hidden=0, file=f"{seat}_itdg{it}_lr{lv_name(lv)}") for it, lv in cond]
            items.insert(int(rng.integers(0, len(items) + 1)), dict(seat=seat, rep=rep, itdg_ms=None, level_ratio_db=None, hidden=1, file=f"{seat}_s00"))
            for x in items:
                n += 1; x.update(block=b, n=n); out.append(x)
    for i, x in enumerate(out, 1):
        x["index"] = i
    return out


def answer(tr, subj, s_lv, s_it, random_responder, rng):
    if random_responder:
        return {q: int(rng.integers(1, 6)) for q in ITEM_K}
    side = tr["seat"] in ("L", "R")
    out = {}
    for q, k in ITEM_K.items():
        if tr["hidden"]:
            mu = 1.6
        else:
            li, ii = LEVELS.index(tr["level_ratio_db"]), ITDGS.index(tr["itdg_ms"])
            inter = -0.30 if (ii == 2 and li >= 3) else 0.0
            mu = 0.9 + k * (LV_MU[li] + IT_MU[ii] + inter + (SIDE_IT[ii] - 0.2 if side else 0)) + s_lv * (li - 2) / 2 + s_it * (ii - 1)
        out[q] = int(np.clip(np.round(mu + subj + rng.normal(0, 1) + 3), 1, 5))
    return out


def session(pid, mode, order, rng, t0, random_responder=False, debug=False, finished=True, cut=None):
    sid = "%016x" % int(rng.integers(0, 2**63))
    subj, s_lv, s_it = rng.normal(0, 0.7), rng.normal(0, 0.3), rng.normal(0, 0.2)
    trs = trials_for(order, rng)
    if cut:
        trs = trs[:cut]
    now = t0 + timedelta(minutes=3)
    rows = []
    for tr in trs:
        a = answer(tr, subj, s_lv, s_it, random_responder, rng)
        listen = float(np.clip(rng.normal(9, 3), 5, 12.1)); rt = listen + max(0, rng.normal(2, 1.5))
        now += timedelta(seconds=rt + 1.4)
        rows.append(dict(session_id=sid, index=tr["index"], block=tr["block"], seat=tr["seat"], rep=tr["rep"], n=tr["n"], file=tr["file"], hidden=tr["hidden"],
                         itdg_ms=tr["itdg_ms"], level_ratio_db=tr["level_ratio_db"], q1=a["q1"], q1_hard=int(rng.random() < 0.08), q2=a["q2"], q3=a["q3"],
                         plays=1 + int(rng.random() < 0.1), listen_s=round(listen, 2), rt_s=round(rt, 2), at=now.isoformat().replace("+00:00", "Z")))
    s = dict(session_id=sid, pid=pid, mode=mode, lang="ja", version="pilot2-0.4", debug=debug, simulated=True, seat_order=order, seat_order_source="server",
             started_at=t0.isoformat().replace("+00:00", "Z"), quiz_attempts=int(1 + (rng.random() < 0.3)))
    if mode == "lab":
        v = int(rng.integers(40, 75)); s.update(volume_setting=f"mac {v}", volume_system=v, volume_system_end=v if rng.random() > 0.05 else v + 6)
    else:
        s.update(headphone="(simulated)", volume_setting="")
    if finished:
        s["finished_at"] = (now + timedelta(minutes=2)).isoformat().replace("+00:00", "Z")
        s["post"] = dict(q1q3_difficult=int(rng.integers(1, 6)), unstable_how="ac", fatigue=int(rng.integers(1, 6)), experience_years=int(rng.integers(0, 15)),
                         hearing_problem="no" if rng.random() > 0.05 else "yes", comments="")
    return s, rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--lab", type=int, default=30); ap.add_argument("--online", type=int, default=8)
    ap.add_argument("--out", default="sim"); ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(); rng = np.random.default_rng(a.seed); os.makedirs(a.out, exist_ok=True)
    t0 = datetime(2027, 3, 1, 1, 0, tzinfo=timezone.utc)
    sessions, trials = [], []

    def add(s, rows, resend=False):
        sessions.append(s)
        for r in rows:
            trials.append(dict(pid=s["pid"], mode=s["mode"], version=s["version"], **r))
        if resend:                                       # a block re-sent after a network error
            for r in rows[20:31]:
                trials.append(dict(pid=s["pid"], mode=s["mode"], version=s["version"], **r))
    for i in range(a.lab):
        add(*session(f"L{i:05X}", "lab", ORDERS[i % 6], rng, t0 + timedelta(hours=i), random_responder=i in (5, 17)), resend=(i == 3))
    for i in range(a.online):
        add(*session(f"W{i:05X}", "online", ORDERS[i % 6], rng, t0 + timedelta(days=1, hours=i)))
    add(*session("LDEBUG", "lab", "LCR", rng, t0, debug=True))
    add(*session("TEST_DELETE_ME", "lab", "CRL", rng, t0))
    add(*session("LCUT01", "lab", "RLC", rng, t0, finished=False, cut=30))
    tdf = pd.DataFrame(trials); tdf.insert(0, "received", "2027-03-01")
    cols = ["received", "pid", "mode", "version", "session_id", "index", "block", "seat", "rep", "n", "file", "hidden", "itdg_ms", "level_ratio_db",
            "q1", "q1_hard", "q2", "q3", "plays", "listen_s", "rt_s", "at"]
    tdf[cols].to_csv(os.path.join(a.out, "trials.csv"), index=False)
    srows = [dict(received="2027-03-01", session_id=s["session_id"], pid=s["pid"], mode=s["mode"], version=s["version"], lang=s["lang"], seat_order=s["seat_order"],
                  n_trials_sent_last=0, session_json=json.dumps(s, ensure_ascii=False)) for s in sessions]
    pd.DataFrame(srows).to_csv(os.path.join(a.out, "sessions.csv"), index=False)
    print(f"SIMULATED: {len(sessions)} sessions, {len(tdf)} trial rows -> {a.out}/")


if __name__ == "__main__":
    main()
