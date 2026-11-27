import unreal, os, glob
d = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir())
f = sorted(glob.glob(os.path.join(d, "*.log")), key=os.path.getmtime)[-1]
for l in open(f, errors="replace").read().split("\n")[-25:]: print(l[:330])
