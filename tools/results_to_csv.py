"""Turn downloaded result files (levelandtiming_*.json) into two CSV tables.
usage: python tools/results_to_csv.py results/*.json   -> sessions.csv, trials.csv in the current folder"""
import csv, json, sys
ses, tri = [], []
for f in sys.argv[1:]:
    d = json.load(open(f, encoding="utf-8")); s = dict(d["session"]); post = s.pop("post", None) or {}
    s.update({"post_" + k: v for k, v in post.items()}); ses.append(s)
    tri += [dict(t, pid=d["session"]["pid"], mode=d["session"]["mode"], seat_order=d["session"]["seat_order"]) for t in d["trials"]]
for name, rows in (("sessions.csv", ses), ("trials.csv", tri)):
    keys = []; [keys.append(k) for r in rows for k in r if k not in keys]
    with open(name, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print(name, len(rows), "rows")
