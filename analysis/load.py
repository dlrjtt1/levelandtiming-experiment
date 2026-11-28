"""Read pilot-2 results into two tables (trials, sessions), from the Google Sheet export or from downloaded result files.

Sheet export: in the spreadsheet, File > Download > CSV for the tabs "trials" and "sessions" (one file each).
Result files: the levelandtiming_<pid>_<session>.json files that participants download when sending fails.

Cleaning done here (nothing that looks at the answers):
- the receiver may get the same trial twice (resend after a network error): keep the last copy of each (session_id, index)
- the sessions tab gets one row per transmission: keep the last row of each session_id
"""
import json
import pandas as pd

TRIAL_NUM = ["index", "block", "rep", "n", "hidden", "itdg_ms", "level_ratio_db", "q1", "q1_hard", "q2", "q3", "plays", "listen_s", "rt_s"]


def _session_table(records):
    rows = []
    for r in records:
        s = dict(r)
        post = s.pop("post", None) or {}
        s.update({"post_" + k: v for k, v in post.items()})
        quiz = s.pop("quiz_wrong", None)
        s["quiz_wrong"] = json.dumps(quiz, ensure_ascii=False) if quiz else ""
        rows.append(s)
    return pd.DataFrame(rows)


def from_sheet(trials_csv, sessions_csv):
    t = pd.read_csv(trials_csv, dtype={"pid": str, "session_id": str})
    s = pd.read_csv(sessions_csv, dtype={"pid": str, "session_id": str})
    t = t.drop_duplicates(["session_id", "index"], keep="last")
    s = s.drop_duplicates("session_id", keep="last")
    recs = []
    for _, row in s.iterrows():
        try:
            j = json.loads(row["session_json"])
        except (TypeError, ValueError):
            j = {}
        for k in ("session_id", "pid", "mode", "version", "lang", "seat_order"):
            j.setdefault(k, row.get(k))
        recs.append(j)
    return _tidy(t, _session_table(recs))


def from_json(files):
    tri, ses = [], []
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        s = d["session"]
        ses.append(s)
        tri += [dict(x, session_id=s["session_id"], pid=s.get("pid"), mode=s.get("mode"), version=s.get("version")) for x in d["trials"]]
    t = pd.DataFrame(tri).drop_duplicates(["session_id", "index"], keep="last")
    s = _session_table(ses).drop_duplicates("session_id", keep="last")
    return _tidy(t, s)


def _tidy(t, s):
    for c in TRIAL_NUM:
        if c in t:
            t[c] = pd.to_numeric(t[c], errors="coerce")
    t["hidden"] = t["hidden"].fillna(0).astype(int)
    for c in ("started_at", "finished_at", "consent_at"):
        if c in s:
            s[c] = pd.to_datetime(s[c], errors="coerce", utc=True)
    if "debug" in s:
        s["debug"] = s["debug"].map(lambda v: str(v).lower() in ("true", "1"))
    else:
        s["debug"] = False
    if "simulated" not in s:
        s["simulated"] = False
    s["simulated"] = s["simulated"].map(lambda v: str(v).lower() in ("true", "1"))
    return t.reset_index(drop=True), s.reset_index(drop=True)
