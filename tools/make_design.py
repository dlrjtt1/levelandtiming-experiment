"""Build web/design.json from the stimulus set's stimuli.csv (and practice.csv).
usage: python tools/make_design.py <set>/stimuli.csv <set>/manifest.json <practice>/practice.csv > web/design.json
File names are the same in the lab (HD600) and online (no EQ) sets, so one design.json serves both."""
import csv, json, sys
rows = list(csv.DictReader(open(sys.argv[1])))
man = json.load(open(sys.argv[2]))
prac = list(csv.DictReader(open(sys.argv[3])))
stem = lambda f: f[:-4]
cond = [dict(file=stem(r["file"]), seat=r["seat"], itdg=int(float(r["itdg_nominal_ms"])), lr=int(float(r["level_ratio_nominal_db"])),
             itdg_eff_BL=float(r["itdg_eff_BL_ms"]), itdg_eff_BR=float(r["itdg_eff_BR_ms"]), lr_eff=float(r["level_ratio_eff_db"]))
        for r in rows if r["type"] == "condition"]
refs = {r["seat"]: stem(r["file"]) for r in rows if r["type"] != "condition"}
seats = sorted({c["seat"] for c in cond}, key="LCR".index)
assert all(sum(c["seat"] == s for c in cond) == len(cond) // len(seats) for s in seats) and set(refs) == set(seats)
out = dict(stimulus_set=dict(brir_sofa_sha256=man["brir_sofa_sha256"], length_s=round(man["length_samples"] / man["fs"], 3), fs=man["fs"]),
           seats=seats, conditions=cond, references=refs,
           hidden={k: k + "_s00" for k in refs},   # hidden reference: copy of <seat>_ref_pathA.wav under a neutral name (tools/hidden_refs.sh)
           practice=[dict(file=stem(r["file"]), seat=r["seat"]) for r in prac if r["role"].startswith("practice")],
           volume=[stem(r["file"]) for r in prac if r["role"] == "volume"][0])
json.dump(out, sys.stdout, indent=1)
