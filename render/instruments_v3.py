# Instruments held by the posed MetaHumans (UE): same layout rules as scene.py player()/singer(),
# but anchored on the MetaHuman landmarks written by cr3_pose.py (_log/landmarks_<Name>.json, UE cm).
# Writes ue/CR3_instruments_v3.fbx (one mesh per performer, named I_<Name>; geometry in world position)
#    and ue/hands_v3.json  (IK targets and pole points for each hand, UE cm) for cr3_pose.py.
# usage: python instruments_v3.py <folder with landmarks_*.json> <layout_ue.csv>
import sys, os, json, csv, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Vector, Matrix
import props as PR

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "ue")
LMD, LAYOUT = sys.argv[-2], sys.argv[-1]
STAGE = 1.0
def cfg(p): return Vector((p[0] / 100.0, -p[1] / 100.0, p[2] / 100.0))       # UE cm -> config m
def ue(v): return [round(v.x * 100, 2), round(-v.y * 100, 2), round(v.z * 100, 2)]
def frame(yaw):
    f = Vector((math.cos(yaw), math.sin(yaw), 0)); l = Vector((0, 0, 1)).cross(f); return f, l, Vector((0, 0, 1))

for o in list(bpy.data.objects): bpy.data.objects.remove(o)
sc = bpy.context.scene
hands = {}

def build(name, part, lm, yaw_cfg, xy):
    f, l, z = frame(yaw_cfg); base = Vector((xy[0], xy[1], STAGE))
    pel, neck, head = cfg(lm["pelvis"]), cfg(lm["neck_01"]), cfg(lm["head"])
    shL, shR = cfg(lm["upperarm_l"]), cfg(lm["upperarm_r"])
    mouth = head + f * 0.09
    H = {}
    def ik(side, t, pole, face=None):
        H[side] = {"t": ue(t), "pole": ue(pole)}
        if face is not None: H[side]["face"] = ue(face)        # the palm is turned towards this point
    if part in ("Violin I", "Violin II", "Viola"):
        k = 1.12 if part == "Viola" else 1.0; L = 0.355 * k
        tail = neck + l * 0.11 - z * 0.03 + f * 0.04
        d = (f * 0.62 + l * 0.72 - z * 0.22).normalized(); upv = (z * 0.8 - l * 0.45 + f * 0.1)
        PR.string_instrument(part.replace(" ", ""), L, 0.04 * k, 0.26 * k, tail, d, upv)
        ik('L', tail + d * (L + 0.17 * k) - z * 0.03, shL + l * 0.3 - z * 0.5)
        bridge = tail + d * (0.42 * L) + z * 0.05; perp = d.cross(z).normalized()
        hand = bridge + perp * 0.25 - z * 0.03 + f * 0.05
        ik('R', hand, shR - l * 0.4 - z * 0.3)
        PR.bow(hand - perp * 0.05, hand - perp * 0.70 + z * 0.06)
    elif part == "Contrabass":
        # standing player: bass at the left front, leaning back to the left hip, top plate turned a little to the bow side.
        # 0.9 scale (a small bass) so that the bridge is within reach of this player's arm.
        L, rib, neckL = 1.0, 0.17, 0.68
        foot = base + f * 0.45 + l * 0.30
        d = (z * 1.0 - f * 0.22).normalized(); n = (f - l * 0.25).normalized()      # n: normal of the top plate
        acr = d.cross(n).normalized()
        if acr.dot(l) > 0: acr = -acr                                                 # across the strings, to the player's right
        tail = foot + d * 0.45
        PR.string_instrument(part, L, rib, neckL, tail, d, n)
        PR.tube(part + "_endpin", foot, tail, 0.006, PR.mat("chrome", (0.6, 0.6, 0.62), 0.2, metal=1.0))
        P = tail + d * (L + neckL * 0.3) + n * 0.03                                   # fingerboard, low position
        ik('L', P + l * 0.035 - z * 0.06 - n * 0.02, shL + l * 0.3 - z * 0.4, face=P)        # wrist below-left of it, fingers continue onto the neck
        contact = tail + d * (0.38 * L + 0.12) + n * (rib + 0.05)
        frog = contact + acr * 0.30 + n * 0.02
        wrist = frog + (shR - frog).normalized() * 0.08                               # the hand bone is the wrist; the grip is 8 cm further
        if (wrist - shR).length > 0.50:
            wrist = shR + (wrist - shR).normalized() * 0.50; frog = wrist + (frog - wrist).normalized() * 0.08
        ik('R', wrist, shR - l * 0.4 - z * 0.3)
        PR.bow(frog, frog + (contact - frog).normalized() * 0.70)
    elif part == "Cello":
        L, rib, neckL = 0.75, 0.12, 0.5
        foot = base + f * 0.45 + l * 0.02
        d = (z * 1.0 - f * 0.42 + l * 0.12).normalized(); tail = foot + d * 0.27
        PR.string_instrument(part, L, rib, neckL, tail, d, f)
        PR.tube(part + "_endpin", foot, tail, 0.006, PR.mat("chrome", (0.6, 0.6, 0.62), 0.2, metal=1.0))
        Pc = tail + d * (L + 0.06) + f * 0.02; ik('L', Pc + l * 0.07 - z * 0.04, shL + l * 0.15 - z * 0.5, face=Pc)
        bridge = tail + d * (0.38 * L) + f * (rib + 0.03); hand = bridge - l * 0.20 + z * 0.10 - f * 0.08
        ik('R', hand, shR - l * 0.4 - z * 0.4)
        PR.bow(hand + l * 0.02, hand + l * 0.68 - z * 0.04 + f * 0.04)
    elif part == "Flute":
        a = mouth - z * 0.04 + l * 0.04; d = (-l * 0.92 + f * 0.25 - z * 0.12).normalized()
        PR.flute(a, d); ik('L', a + d * 0.14, shL + l * 0.2 - z * 0.5); ik('R', a + d * 0.45, shR - l * 0.5 - z * 0.3)
    elif part == "Clarinet":
        a = mouth - z * 0.03; d = (f * 0.55 - z * 0.83).normalized()
        PR.clarinet(a, d); ik('L', a + d * 0.22, shL + l * 0.4 - z * 0.3); ik('R', a + d * 0.45, shR - l * 0.4 - z * 0.3)
    elif part == "Bassoon":
        b0 = pel + f * 0.28 - l * 0.16 - z * 0.15; ax = (z * 1.0 + l * 0.22 + f * 0.05).normalized()
        PR.bassoon(b0, ax, mouth - z * 0.02)
        ik('L', b0 + ax * 0.78 + f * 0.04, shL + l * 0.4 - z * 0.3); ik('R', b0 + ax * 0.38 + f * 0.04 - l * 0.02, shR - l * 0.4 - z * 0.3)
    elif part.startswith("Horn"):
        c = pel + f * 0.25 - l * 0.12 + z * 0.32
        PR.horn(c, l, (-l * 0.6 - f * 0.4 - z * 0.7))
        ik('L', c + l * 0.02 + z * 0.05 + f * 0.02, shL + l * 0.4 - z * 0.3)
        ik('R', c - l * 0.2 - z * 0.12 - f * 0.08, shR - l * 0.4 - z * 0.3)
    elif part == "Singer":
        waist = cfg(lm["spine_03"]) + f * 0.17 - z * 0.06
        ik('L', waist + l * 0.03, shL + l * 0.4 - z * 0.3 - f * 0.2); ik('R', waist - l * 0.03 + z * 0.02, shR - l * 0.4 - z * 0.3 - f * 0.2)
    if part == "Singer":   # floor-length skirt of the gown (deep blue satin); the bodice is the overlay material in UE (cr3_cloth.py)
        satin = PR.mat("satin", (0.02, 0.035, 0.14), 0.42, sheen=0.25)
        h = pel.z - 0.03 - STAGE          # skirt starts at the hips so that the elbows and forearms stay outside it
        prof = [(0.165, h), (0.185, h - 0.06), (0.20, h - 0.18), (0.215, h - 0.34), (0.23, h - 0.55), (0.25, 0.32), (0.285, 0.1), (0.31, 0.01), (0.312, 0.0)]
        c = (cfg(lm["foot_l"]) + cfg(lm["foot_r"])) / 2 * 0.5 + pel * 0.5 + f * 0.03
        g = PR.lathe("gown", prof, satin, (c.x, c.y, STAGE), segs=96, scale=(0.95, 1.0, 1.0))
        g.rotation_euler.z = yaw_cfg
        g.data.flip_normals()          # outside faces outwards (UE draws one side only)
        tex = bpy.data.textures.new("folds", 'WOOD'); tex.wood_type = 'BANDNOISE'; tex.noise_scale = 0.06; tex.turbulence = 3.0
        g.modifiers.new("sub", 'SUBSURF').levels = 2
        dm = g.modifiers.new("folds", 'DISPLACE'); dm.texture = tex; dm.strength = 0.01; dm.texture_coords = 'LOCAL'
    hands[name] = H

dg = None
def realize(objs, nm):
    global dg
    dg = bpy.context.evaluated_depsgraph_get(); bm = bmesh.new(); mats = []
    def add(o, M):
        if o.type in ('MESH', 'CURVE'):
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); me.transform(M @ o.matrix_world)
            for m in me.materials:
                if m not in mats: mats.append(m)
            remap = [mats.index(m) for m in me.materials]
            tmp = bmesh.new(); tmp.from_mesh(me)
            for fc in tmp.faces: fc.material_index = remap[fc.material_index] if remap else 0
            me2 = bpy.data.meshes.new("t"); tmp.to_mesh(me2); tmp.free(); bm.from_mesh(me2)
            bpy.data.meshes.remove(me); bpy.data.meshes.remove(me2)
        elif o.type == 'EMPTY' and o.instance_type == 'COLLECTION' and o.instance_collection:
            for c in o.instance_collection.objects: add(c, M @ o.matrix_world)
        for ch in o.children: add(ch, M)
    for o in objs: add(o, Matrix.Identity(4))
    me = bpy.data.meshes.new(nm); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    ob = bpy.data.objects.new(nm, me); sc.collection.objects.link(ob); return ob

out = []
for r in csv.DictReader(open(LAYOUT)):
    name = r["name"]
    if name.startswith("SeatCam"): continue
    lm = json.load(open(os.path.join(LMD, f"landmarks_{name}.json")))
    before = set(bpy.data.objects)
    build(name, r["what"] if name != "Singer" else "Singer", lm, math.radians(-float(r["UE_yaw_deg"])), (float(r["config_x_m"]), float(r["config_y_m"])))
    new = [o for o in bpy.data.objects if o not in before and o.parent is None]
    if new: out.append(realize(new, "I_" + name)); [bpy.data.objects.remove(o, do_unlink=True) for o in new if o.name in bpy.data.objects]
for o in list(bpy.data.objects):
    if o not in out: bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
for o in out: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "CR3_instruments_v3.fbx"), use_selection=True, object_types={'MESH'},
                         apply_scale_options='FBX_SCALE_ALL', path_mode='STRIP', mesh_smooth_type='FACE', add_leaf_bones=False)
json.dump(hands, open(os.path.join(OUT, "hands_v3.json"), "w"), indent=1)
print("wrote", [o.name for o in out])
