# Export everything except the hall surfaces for Unreal Engine (FBX, metres in Blender -> centimetres in UE):
#   CR3_audience_chairs.fbx   ground-floor audience chairs (one mesh)
#   CR3_PA.fbx                two PA loudspeakers on stands (assumed positions of the stimuli)
#   CR3_stage_props.fbx       orchestra chairs and music stands
#   CR3_instruments.fbx       instruments and bows, placed as held by the Rocketbox stand-ins (starting point only)
#   CR3_markers_cameras.fbx   seat cameras L/C/R, floor markers for the 11 performers (arrow = facing), axis check
#   layout_ue.csv             the same positions as numbers
# usage: python export_ue.py      (needs the Rocketbox assets, see get_assets.sh; run bake_hall.py for the hall)
import sys, os, math, json, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Vector, Matrix
import scene as S
import props as PR

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "ue"); os.makedirs(OUT, exist_ok=True)
INFO = S.INFO
sc = S.build()
dg = bpy.context.evaluated_depsgraph_get()

def realize(objs, name):
    """bake modifiers, curves and collection instances into one mesh object"""
    bm = bmesh.new(); mats = []
    def add(o, M):
        if o.type in ('MESH', 'CURVE'):
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); me.transform(M @ o.matrix_world)
            for m in me.materials:
                if m not in mats: mats.append(m)
            remap = [mats.index(m) for m in me.materials]
            tmp = bmesh.new(); tmp.from_mesh(me)
            for f in tmp.faces: f.material_index = remap[f.material_index] if remap else 0
            me2 = bpy.data.meshes.new("t"); tmp.to_mesh(me2); tmp.free(); bm.from_mesh(me2)
            bpy.data.meshes.remove(me); bpy.data.meshes.remove(me2)
        elif o.type == 'EMPTY' and o.instance_type == 'COLLECTION' and o.instance_collection:
            for c in o.instance_collection.objects: add(c, M @ o.matrix_world)
        for ch in o.children: add(ch, M)
    for o in objs: add(o, Matrix.Identity(4))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); return ob

def export(objs, name, types={'MESH'}):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"), use_selection=True, object_types=types,
                             apply_scale_options='FBX_SCALE_ALL', path_mode='STRIP', mesh_smooth_type='FACE', add_leaf_bones=False)
    print("wrote", name, flush=True)

objs = list(bpy.data.objects)
top = [o for o in objs if o.parent is None]
pick = lambda *pre: [o for o in top if any(o.name.startswith(p) for p in pre)]
export([realize(pick("chair_"), "AudienceChairs")], "CR3_audience_chairs")
export([realize(pick("pa_"), "PA_Loudspeakers")], "CR3_PA")
export([realize(pick("oc_"), "OrchestraChairs"), realize(pick("ms_"), "MusicStands")], "CR3_stage_props")
inst = [o for o in top if o.type in ('EMPTY',) and o.instance_type != 'COLLECTION' and any(o.name.startswith(p) for p in ("Violin", "Viola", "Cello", "Contrabass"))]
inst_objs = []
for o in inst: inst_objs.append(realize([o], o.name))
for pre in ("Cello_endpin", "Contrabass_endpin"):
    inst_objs += [realize([o], o.name) for o in top if o.name.startswith(pre)]
for pre, nm in (("bow_", "Bows"), ("flute", "Flute"), ("clarinet", "Clarinet"), ("bassoon", "Bassoon"), ("bocal", "Bassoon_bocal"), ("horn_", "Horns")):
    sel = pick(pre)
    if sel: inst_objs.append(realize(sel, nm))
export(inst_objs, "CR3_instruments")

# ---- markers (arrows on the floor: tip = the way the person faces), seat cameras, axis check
marker_mat = PR.mat("marker", (1.0, 0.25, 0.0), 0.6); cam_objs, marks, rows = [], [], []
def arrow(name, x, y, z, yaw, size=0.35):
    me = bpy.data.meshes.new(name); s = size
    me.from_pydata([(-s, -s * 0.5, 0), (s * 0.2, -s * 0.5, 0), (s * 0.2, -s, 0), (s * 1.2, 0, 0), (s * 0.2, s, 0), (s * 0.2, s * 0.5, 0), (-s, s * 0.5, 0)], [], [(0, 1, 5, 6), (2, 3, 4)])
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); me.materials.append(marker_mat)
    o.location = (x, y, z + 0.01); o.rotation_euler.z = yaw; marks.append(o); return o
def ue(p):   # config metres -> UE centimetres (FBX import flips Y: Unreal is left-handed)
    return tuple(round(v * 100, 1) + 0.0 for v in (p[0], -p[1], p[2]))
def ue_yaw(yaw):
    return round(-math.degrees(yaw), 1) + 0.0

sp = INFO["singer"]; yaw = S.heading(sp[:2], (9.0, 0.0)); arrow("MARK_Singer", sp[0], sp[1], S.STAGE, yaw)
rows.append(dict(name="Singer", part="soprano (amplified source, path A)", posture="standing", x=sp[0], y=sp[1], z_floor=S.STAGE, z_source=sp[2], yaw=yaw))
for p in INFO["players"]:
    yaw = S.heading(p["pos"][:2], (4.0, 0.0)); nm = "MARK_" + p["part"].replace(" ", "")
    arrow(nm, p["pos"][0], p["pos"][1], S.STAGE, yaw)
    rows.append(dict(name=p["part"].replace(" ", ""), part=p["part"], posture="standing" if p["part"] == "Contrabass" else "seated",
                     x=p["pos"][0], y=p["pos"][1], z_floor=S.STAGE, z_source=p["pos"][2], yaw=yaw))
for s, pos in INFO["seats"].items():
    cd = bpy.data.cameras.new("SeatCam_" + s); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.sensor_height = 20.25
    cd.lens = 18.0 / math.tan(math.radians(47)); cd.clip_start = 0.05
    c = bpy.data.objects.new("SeatCam_" + s, cd); sc.collection.objects.link(c); c.location = pos
    c.rotation_euler = (math.radians(90), 0, math.radians(90)); cam_objs.append(c)
    rows.append(dict(name="SeatCam_" + s, part="camera, ear position of seat " + s, posture="-", x=pos[0], y=pos[1], z_floor=0.0, z_source=pos[2], yaw=math.pi))
# axis check: a 1 m red bar along +x (towards the audience) and a 1 m green bar along +y (to the right seen from the audience)
ax = []
for nm, d, col in (("AXIS_plus_x_to_audience", (1, 0, 0), (1, 0, 0)), ("AXIS_plus_y_right_seen_from_audience", (0, 1, 0), (0, 1, 0))):
    o = PR.cyl(nm, 0.03, 1.0, (0, 0, 0.05), d, PR.mat(nm, col, 0.5)); ax.append(o)
export(marks + cam_objs + ax, "CR3_markers_cameras", types={'MESH', 'CAMERA'})

with open(os.path.join(OUT, "layout_ue.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["name", "what", "posture", "config_x_m", "config_y_m", "floor_z_m", "source_or_ear_z_m", "UE_X_cm", "UE_Y_cm", "UE_Z_floor_cm", "UE_Z_source_or_ear_cm", "UE_yaw_deg"])
    for r in rows:
        u = ue((r["x"], r["y"], r["z_floor"])); us = ue((r["x"], r["y"], r["z_source"]))
        w.writerow([r["name"], r["part"], r["posture"], r["x"], r["y"], r["z_floor"], r["z_source"], u[0], u[1], u[2], us[2], ue_yaw(r["yaw"])])
print("layout written", flush=True)
