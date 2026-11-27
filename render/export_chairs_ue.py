# Re-export only the audience chairs for UE (ue/CR3_audience_chairs.fbx), without building the performers.
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Matrix
from hall import reset
import props as PR
HERE = os.path.dirname(os.path.abspath(__file__)); INFO = json.load(open(os.path.join(HERE, "scene.json")))
sc = reset(); PR.audience_chairs(INFO["seats"]["C"][0]); dg = bpy.context.evaluated_depsgraph_get()
bm = bmesh.new(); mats = []
for o in [o for o in bpy.data.objects if o.name.startswith("chair_")]:
    for c in o.instance_collection.objects:
        me = bpy.data.meshes.new_from_object(c.evaluated_get(dg)); me.transform(o.matrix_world @ c.matrix_world)
        for m in me.materials:
            if m not in mats: mats.append(m)
        remap = [mats.index(m) for m in me.materials]
        for p in me.polygons: p.material_index = remap[p.material_index]
        bm.from_mesh(me); bpy.data.meshes.remove(me)
me = bpy.data.meshes.new("AudienceChairs"); bm.to_mesh(me); bm.free()
for m in mats: me.materials.append(m)
ob = bpy.data.objects.new("AudienceChairs", me); sc.collection.objects.link(ob)
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(HERE, "ue", "CR3_audience_chairs.fbx"), use_selection=True, object_types={'MESH'},
                         apply_scale_options='FBX_SCALE_ALL', path_mode='STRIP', mesh_smooth_type='FACE', add_leaf_bones=False)
print("chairs:", len(me.vertices), "verts; materials", [m.name for m in mats])
