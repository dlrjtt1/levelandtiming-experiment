import unreal, os, sys, glob
d = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir())
fs = sorted(glob.glob(os.path.join(d, "*.log")), key=os.path.getmtime)
pat = [a.lower() for a in sys.argv[1:]] or ["metahuman", "autorig", "eula", "login", "auth"]
print(d, [os.path.basename(f) for f in fs][-3:])
lines = open(fs[-1], errors="replace").read().split("\n")
for l in [l for l in lines if any(p in l.lower() for p in pat)][-40:]: print(l[:400])
