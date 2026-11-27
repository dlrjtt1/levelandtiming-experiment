# sh run.sh <id> cr3_pose_all.py   -> pose every performer from layout_ue.csv (posture column), then cr3_seq.py shows them
import runpy, sys, os, csv
HERE = os.path.dirname(os.path.abspath(__file__))
rows = [r for r in csv.DictReader(open(os.path.join(HERE, "layout_ue.csv"))) if not r["name"].startswith("SeatCam")]
for r in rows:
    sys.argv = ["cr3_pose.py", r["name"], "seated" if r["posture"] == "seated" else "standing"]
    try: runpy.run_path(os.path.join(HERE, "cr3_pose.py"), run_name="__main__"); print(r["name"], "ok")
    except Exception as e: print(r["name"], "FAILED", e)
