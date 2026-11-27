"""Build render/cr3.obj and render/scene.json from the AuralPaths config used for the stimuli.
usage: python tools/make_scene.py cr3_pilot2_mozart_config.json
The OBJ is the BRAS CR3 model (Aspoeck et al. 2020, CC BY-SA 4.0) as stored in the config; scene.json holds the
source and seat positions in config coordinates (x towards the audience, y to the right seen from the audience, z up)."""
import json, os, sys
c = json.load(open(sys.argv[1])); out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "render")
m = c["geometry"]["mesh"]
open(os.path.join(out, "cr3.obj"), "w").write(m["obj_text"])
src = {k: v for k, v in c["sources"].items() if isinstance(v, dict) and "pos" in v}
scene = dict(note="Positions from the AuralPaths config of pilot 2. PA and performer positions are assumed (CR3 has no PA).",
             up_axis=m.get("up", "y"), listener_view=[-1, 0, 0],
             singer=src["S_amp"]["pos"], pa=[src["B_L"]["pos"], src["B_R"]["pos"]],
             players=[dict(pos=v["pos"], part=v.get("role", "").split(",")[0]) for k, v in src.items() if k.startswith("S_unamp")],
             seats=c["receivers"])
# BRAS CR3 360° panorama (Pictures/CR3_360panorama.jpg), projected onto the model from the point where it was taken.
# Pose fitted by matching model edges to the photo's edges (tools/fit_pano.py): config (x, y, z), yaw in degrees.
scene["pano"] = dict(file="CR3_360panorama.jpg", pos=[7.7, 0.0, 1.7], yaw_deg=0.0)
json.dump(scene, open(os.path.join(out, "scene.json"), "w"), indent=1)
print({k: (v if k != "players" else len(v)) for k, v in scene.items() if k != "note"}, "| mesh keys", [k for k in m if k != "obj_text"])
