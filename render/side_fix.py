# Covers the side podiums (|y| 5.59-6.22 m, 0.45 m high), where the panorama's loose chairs are smeared over the hall model:
# a dark wooden podium box, a dado panel in front of the wall base, and one line of 3D chairs facing the stage on each side.
# Writes ue/CR3_sidefix.fbx (one mesh, world position).   usage: python side_fix.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Matrix
from hall import reset
import props as PR
HERE = os.path.dirname(os.path.abspath(__file__))
sc = reset(); col = PR.audience_chair_collection()
wood = PR.mat("side_wood", (0.075, 0.034, 0.015), 0.5); rail = PR.mat("side_rail", (0.11, 0.052, 0.022), 0.42)
X0, X1 = -0.6, 13.1; objs = []
import json; EAR_X = json.load(open(os.path.join(HERE, 'scene.json')))['seats']['C'][0]
for sgn in (-1, 1):
    # wainscot in front of the podium and the column bases (y = 5.62 m), floor to 1.5 m: panel, stiles, base and cap rail
    Y = sgn * 5.62; inn = -sgn       # inn: towards the audience
    objs.append(PR.box(f"side_panel_{sgn}", (X1 - X0, 0.05, 1.5), ((X0 + X1) / 2, Y, 0.75), wood))
    objs.append(PR.box(f"side_base_{sgn}", (X1 - X0, 0.03, 0.16), ((X0 + X1) / 2, Y + inn * 0.035, 0.08), rail))
    objs.append(PR.box(f"side_cap_{sgn}", (X1 - X0, 0.09, 0.06), ((X0 + X1) / 2, Y + inn * 0.02, 1.5), rail, 0.01))
    objs.append(PR.box(f"side_mid_{sgn}", (X1 - X0, 0.02, 0.07), ((X0 + X1) / 2, Y + inn * 0.03, 1.36), rail))
    x = X0 + 0.3
    while x < X1:
        objs.append(PR.box(f"side_stile_{sgn}_{x:.1f}", (0.08, 0.02, 1.2), (x, Y + inn * 0.03, 0.16 + 0.6), rail)); x += 1.15
    # the audience rows continued towards the wall (same rows and spacing as PR.audience_chairs): two more chairs per row and side
    rows = [EAR_X - 0.05 - k * 0.92 for k in range(0, 13) if EAR_X - 0.05 - k * 0.92 >= 1.9] + [EAR_X - 0.05 + k * 0.92 for k in range(1, 4)]
    for rx in rows:
        for j in (1, 2):
            o = bpy.data.objects.new(f"sidechair_{sgn}_{rx:.1f}_{j}", None); o.instance_type = 'COLLECTION'; o.instance_collection = col
            o.location = (rx, sgn * (4 + j * 8 / 14), 0); sc.collection.objects.link(o); objs.append(o)
for o in objs:
    if o.name not in sc.collection.objects: sc.collection.objects.link(o)
dg = bpy.context.evaluated_depsgraph_get(); bm = bmesh.new(); mats = []
def add(o, M):
    if o.type == 'MESH':
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); me.transform(M @ o.matrix_world)
        for m in me.materials:
            if m not in mats: mats.append(m)
        remap = [mats.index(m) for m in me.materials]
        for p in me.polygons: p.material_index = remap[p.material_index]
        bm.from_mesh(me); bpy.data.meshes.remove(me)
    elif o.instance_type == 'COLLECTION':
        for c in o.instance_collection.objects: add(c, M @ o.matrix_world)
for o in objs: add(o, Matrix.Identity(4))
me = bpy.data.meshes.new("SideFix"); bm.to_mesh(me); bm.free()
for m in mats: me.materials.append(m)
ob = bpy.data.objects.new("SideFix", me); sc.collection.objects.link(ob)
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(HERE, "ue", "CR3_sidefix.fbx"), use_selection=True, object_types={'MESH'},
                         apply_scale_options='FBX_SCALE_ALL', path_mode='STRIP', mesh_smooth_type='FACE', add_leaf_bones=False)
print("sidefix:", len(me.vertices), "verts", [m.name for m in mats])
