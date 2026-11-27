# Bake the projected BRAS photo into UV textures so the hall can be used in Unreal Engine (or anywhere) as an ordinary mesh.
# Writes ue/CR3_hall.fbx (walls, ceiling, balconies: photo, to be shown as emissive), ue/CR3_stagefloor.fbx (lit),
# ue/CR3_audiencefloor.fbx (parquet) and their textures.
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Vector
from hall import reset, load_hall, pano_copy, P0
import props as PR
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "ue"); os.makedirs(OUT, exist_ok=True)
RES = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4096; GROUPS = 8

sc = reset(); hall, img = load_hall(pano_copy())
bpy.ops.object.select_all(action='DESELECT')
for o in hall: o.select_set(True)
bpy.context.view_layer.objects.active = hall[0]
if len(hall) > 1: bpy.ops.object.join()
H = bpy.context.view_layer.objects.active; H.name = "CR3_hall"
# split: stage floor (material index 1, set in load_hall) into its own object; audience-level floor/seating faces removed
# (the parquet plane and the 3D chairs replace them)
SF = H.copy(); SF.data = H.data.copy(); SF.name = "CR3_stagefloor"; sc.collection.objects.link(SF)
def keep(obj, pred):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not pred(f)], context='FACES'); bm.to_mesh(obj.data); bm.free()
audience = lambda f: abs(f.normal.z) > 0.99 and max(v.co.z for v in f.verts) < 0.05 and min(v.co.x for v in f.verts) > -1.3
keep(SF, lambda f: f.material_index == 1)
keep(H, lambda f: f.material_index != 1 and not audience(f))
print("faces: hall", len(H.data.polygons), "stage floor", len(SF.data.polygons), flush=True)

def weight(f):
    """texel density weight: full where the listeners look (stage, side walls in front of the seats), less behind them
    and on the ceiling"""
    c = f.calc_center_median()
    w = 1.0
    if c.x > 9.5: w = 0.3                      # behind the listener rows
    if c.z > 7.0: w *= 0.6                     # ceiling
    return w

def pack_faces(faces, uvl, res, pad_px=6):
    """one chart per polygon (the model is made of flat faces), projected on its own plane, size x weight,
    shelf-packed into the unit square (the UV operators need a window, which a background run does not have)"""
    charts = []
    for f in faces:
        n = f.normal.normalized(); t = (Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))).cross(n).normalized(); u = n.cross(t)
        k = weight(f); pts = [(v.co.dot(t) * k, v.co.dot(u) * k) for v in f.verts]; x0 = min(p[0] for p in pts); y0 = min(p[1] for p in pts)
        charts.append((f, [(px - x0, py - y0) for px, py in pts], max(p[0] for p in pts) - x0, max(p[1] for p in pts) - y0))
    charts.sort(key=lambda c: -c[3]); pad = pad_px / res
    def place(scale):
        x = y = shelf = 0.0; out = []
        for f, pts, w, h in charts:
            W, Hh = w * scale, h * scale
            if x + W + pad > 1: x = 0.0; y += shelf + pad; shelf = 0.0
            if y + Hh + pad > 1: return None
            out.append((f, pts, x + pad / 2, y + pad / 2)); x += W + pad; shelf = max(shelf, Hh)
        return out
    lo, hi = 0.0, 1.0
    while place(hi) is not None: hi *= 2
    for _ in range(30):
        mid = (lo + hi) / 2
        if place(mid) is None: hi = mid
        else: lo = mid
    for f, pts, ox, oy in place(lo):
        for l, (px, py) in zip(f.loops, pts): l[uvl].uv = (ox + px * lo, oy + py * lo)
    return lo * res

def unwrap_and_bake(o, res, name, groups=1):
    """faces split into `groups` material slots, each with its own res x res texture"""
    src_mats = list(o.data.materials)
    bm = bmesh.new(); bm.from_mesh(o.data); uvl = bm.loops.layers.uv.verify()
    faces = sorted(bm.faces, key=lambda f: -f.calc_area() * weight(f) ** 2); load = [0.0] * groups; grp = [[] for _ in range(groups)]
    for f in faces:
        g = load.index(min(load)); grp[g].append(f); load[g] += f.calc_area() * weight(f) ** 2 + 0.02
    dens = []
    for g, fs in enumerate(grp):
        for f in fs: f.material_index = g
        dens.append(pack_faces(fs, uvl, res))
    bm.to_mesh(o.data); bm.free()
    print(o.name, "texel density (weight 1) px/m:", [round(d) for d in dens], flush=True)
    # one object per group, baked one at a time (8 bake buffers at once do not fit in memory)
    parts = []
    for g in range(groups):
        po = o.copy(); po.data = o.data.copy(); po.name = f"{o.name}_{g}" if groups > 1 else o.name; sc.collection.objects.link(po)
        bm = bmesh.new(); bm.from_mesh(po.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != g], context='FACES'); bm.to_mesh(po.data); bm.free()
        po.data.materials.clear(); m = src_mats[0].copy(); m.name = f"bake_{name}_{g}"; po.data.materials.append(m)
        for p in po.data.polygons: p.material_index = 0
        parts.append(po)
    bpy.data.objects.remove(o, do_unlink=True)
    paths = []
    for g, po in enumerate(parts):
        tname = f"{name}_{g}" if groups > 1 else name
        tex = bpy.data.images.new(tname, res, res, alpha=False)
        m = po.data.materials[0]; n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.image = tex; m.node_tree.nodes.active = n
        bpy.ops.object.select_all(action='DESELECT'); po.select_set(True); bpy.context.view_layer.objects.active = po
        sc.cycles.samples = 4; sc.render.bake.margin = 8
        bpy.ops.object.bake(type='EMIT')
        tex.filepath_raw = os.path.join(OUT, tname + ".png"); tex.file_format = 'PNG'; tex.save(); paths.append(tex.filepath_raw)
        m.node_tree.nodes.remove(n); bpy.data.images.remove(tex)
        print("baked", tname, flush=True)
    return parts, paths

# stage floor: bake the photo as plain emission (strength 1) -> base colour
for m in SF.data.materials:
    nt = m.node_tree; em = next(n for n in nt.nodes if n.type == 'EMISSION'); em.inputs['Strength'].default_value = 1.0
(SF,), sf_tex = unwrap_and_bake(SF, 4096, "T_CR3_stagefloor")
HP, hall_tex = unwrap_and_bake(H, RES, "T_CR3_hall", groups=GROUPS)

def plain_material(o, tex_paths, name):
    o.data.materials.clear()
    for i, tp in enumerate(tex_paths):
        m = bpy.data.materials.new(f"{name}_{i}" if len(tex_paths) > 1 else name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(tp); nt.links.new(t.outputs[0], b.inputs['Base Color'])
        o.data.materials.append(m)
for i, (po, tp) in enumerate(zip(HP, hall_tex)): plain_material(po, [tp], f"M_CR3_hall_photo_{i}")
plain_material(SF, sf_tex, "M_CR3_stagefloor")

def export(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"), use_selection=True, object_types={'MESH', 'CAMERA', 'EMPTY'},
                             apply_scale_options='FBX_SCALE_ALL', bake_space_transform=False, path_mode='STRIP', mesh_smooth_type='FACE', add_leaf_bones=False)
export(HP, "CR3_hall"); export([SF], "CR3_stagefloor")

# audience floor: parquet plane with UVs in metres / 1.2 (one texture repeat = 1.2 m)
pq = PR.parquet(os.path.join(OUT, "T_parquet.jpg"))
me = bpy.data.meshes.new("audience_floor"); verts = [(-0.75, -6.9, 0.003), (16.0, -6.9, 0.003), (16.0, 6.9, 0.003), (-0.75, 6.9, 0.003)]
me.from_pydata(verts, [], [(0, 1, 2, 3)]); uv = me.uv_layers.new(name="UVMap")
for li, l in enumerate(me.loops): v = verts[l.vertex_index]; uv.data[li].uv = (v[0] / 1.2, v[1] / 1.2)
F = bpy.data.objects.new("CR3_audiencefloor", me); sc.collection.objects.link(F); plain_material(F, [pq], "M_parquet")
export([F], "CR3_audiencefloor")
print("baked", RES)
