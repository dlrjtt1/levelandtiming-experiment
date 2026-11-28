"""Participant screening for pilot 2 (criteria fixed before looking at the data; project doc 2026-11-25_pilot2_short_version).
usage: python tools/screening.py results/*.json   -> screening.csv in the current folder

A (main):  hidden reference (path A only, same sound as the seat reference) rated Q2 <= 2 in 2 or more of the 4 hidden trials.
B (extra): centre seat, repetition 1 vs 2 of the same 15 conditions: mean |difference| over Q1-Q3 >= 1.6.
           1.6 is the expected |difference| of two independent uniform answers on 1..5 (2/25 * sum d(5-d), d = 1..4),
           i.e. B removes only participants who are no more consistent than random answering.
C (eligibility, decided 2026-11-28 before any data): answered "yes" to the post-question on hearing problems ("dk" is kept).
All criteria are independent of the condition effects under test. Report the analysis with and without the excluded participants."""
import csv, json, sys
A_Q2_MAX, A_MIN_FAILS, B_LIMIT = 2, 2, 1.6
rows = []
for f in sys.argv[1:]:
    d = json.load(open(f, encoding="utf-8")); s = d["session"]; tr = d["trials"]
    hid = [t for t in tr if t.get("hidden")]
    a_fails = sum(t["q2"] <= A_Q2_MAX for t in hid)
    c = {}
    for t in tr:
        if t["seat"] == "C" and not t.get("hidden"): c.setdefault(t["file"], {})[t["rep"]] = t
    pairs = [v for v in c.values() if 1 in v and 2 in v]
    diffs = [abs(p[1][q] - p[2][q]) for p in pairs for q in ("q1", "q2", "q3")]
    b = round(sum(diffs) / len(diffs), 3) if diffs else None
    exC = str((s.get("post") or {}).get("hearing_problem", "")).lower() == "yes"
    exA = len(hid) > 0 and a_fails >= A_MIN_FAILS
    exB = b is not None and b >= B_LIMIT
    rows.append(dict(file=f, pid=s.get("pid"), mode=s.get("mode"), version=s.get("version"), debug=s.get("debug"), n_trials=len(tr),
                     hidden_n=len(hid), hidden_q2=" ".join(str(t["q2"]) for t in hid), hidden_q1=" ".join(str(t["q1"]) for t in hid), hidden_q3=" ".join(str(t["q3"]) for t in hid),
                     A_fails=a_fails, C_pairs=len(pairs), B_mean_abs_diff=b, quiz_attempts=s.get("quiz_attempts"), quiz_wrong=json.dumps(s.get("quiz_wrong", {})),
                     q1_hard_rate=round(sum(t.get("q1_hard", 0) for t in tr) / len(tr), 3) if tr else None,
                     exclude_A=int(exA), exclude_B=int(exB), exclude_C=int(exC), exclude=int(exA or exB or exC)))
with open("screening.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "participants,", sum(r["exclude"] for r in rows), "excluded (A:", sum(r["exclude_A"] for r in rows), " B:", sum(r["exclude_B"] for r in rows), " C:", sum(r["exclude_C"] for r in rows), ")")
