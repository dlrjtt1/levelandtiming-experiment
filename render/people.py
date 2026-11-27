import bpy, os, math
from mathutils import Vector, Matrix
RB = os.environ.get('ROCKETBOX', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'microsoft-rocketbox')) + '/Assets/'

def _relink(folder):
    tex = os.path.join(folder, 'Textures')
    files = {f.lower(): os.path.join(tex, f) for f in os.listdir(tex)} if os.path.isdir(tex) else {}
    for img in bpy.data.images:
        b = os.path.basename(img.filepath).lower()
        if b in files and not img.get('relinked'):
            img.filepath = files[b]; img['relinked'] = 1; img.reload()

def _fix_materials(objs):
    for o in objs:
        for slot in o.material_slots:
            m = slot.material
            if not m or m.get('fixed'): continue
            m['fixed'] = 1; nt = m.node_tree; n = nt.nodes
            bsdf = next((x for x in n if x.type == 'BSDF_PRINCIPLED'), None)
            if not bsdf: continue
            bsdf.inputs['Roughness'].default_value = 0.6
            # remove specular texture link (3ds Max specular maps are not PBR); keep color + normal
            for lk in list(nt.links):
                if lk.to_node == bsdf and lk.to_socket.name.startswith('Specular'): nt.links.remove(lk)
            col = bsdf.inputs['Base Color'].links[0].from_node if bsdf.inputs['Base Color'].links else None
            if 'opacity' in m.name.lower() and col is not None:   # hair, lashes: alpha from the texture
                nt.links.new(col.outputs['Alpha'], bsdf.inputs['Alpha'])
            if 'head' in m.name.lower() or 'body' in m.name.lower():
                bsdf.inputs['Subsurface Weight'].default_value = 0.08
                bsdf.inputs['Subsurface Radius'].default_value = (0.8, 0.35, 0.2)
                bsdf.inputs['Subsurface Scale'].default_value = 0.01

def load_avatar(rel, action_fbx=None, name=None):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=RB + 'Avatars/' + rel + '/Export/' + os.path.basename(rel) + '.fbx')
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE'); meshes = [o for o in new if o.type == 'MESH']
    _relink(RB + 'Avatars/' + rel); _fix_materials(meshes)
    if action_fbx:   # pose from a Rocketbox animation: copy each bone's world matrix from the animation's own armature
        b2 = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=RB + 'Animations/all_animations_max_motextr_static/' + action_fbx)
        extra = [o for o in bpy.data.objects if o not in b2]
        src = next(o for o in extra if o.type == 'ARMATURE')
        bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
        arm.animation_data_clear(); arm.matrix_world = src.matrix_world.copy(); bpy.context.view_layer.update()
        for pb in arm.pose.bones:   # parents first
            if pb.name in src.pose.bones:
                pb.matrix = arm.matrix_world.inverted() @ src.matrix_world @ src.pose.bones[pb.name].matrix
                bpy.context.view_layer.update()
        for o in extra: bpy.data.objects.remove(o, do_unlink=True)
    for o in new:
        if o.type == 'EMPTY': o.hide_render = True
    if name: arm.name = name
    return arm, meshes

def bone_world(arm, name, tail=False):
    pb = arm.pose.bones[name]; return arm.matrix_world @ (pb.tail if tail else pb.head)

def place(arm, xy, floor_z, yaw):
    """move the posed avatar so its pelvis is above xy, feet on floor_z, facing direction yaw (radians, 0 = +x)"""
    bpy.context.view_layer.update()
    # avatars face -y in their own frame: turn so that they face +x, then by yaw
    R = Matrix.Rotation(yaw + math.pi / 2, 4, 'Z')
    M = arm.matrix_world.copy()
    pel = M @ arm.pose.bones['Bip01 Pelvis'].head
    feet = min((M @ arm.pose.bones[b].tail).z for b in ('Bip01 L Toe0', 'Bip01 R Toe0') if b in arm.pose.bones) if 'Bip01 L Toe0' in arm.pose.bones else 0.0
    T0 = Matrix.Translation(Vector((-pel.x, -pel.y, -feet)))
    arm.matrix_world = Matrix.Translation(Vector((xy[0], xy[1], floor_z))) @ R @ T0 @ M
    bpy.context.view_layer.update()

def _rotate_bone_world(arm, pb, pivot, q):
    TW = arm.matrix_world
    W = TW @ pb.matrix
    W2 = Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ W
    pb.matrix = TW.inverted() @ W2
    bpy.context.view_layer.update()

def ik(arm, side, target, pole=None, elbow_hint=None):
    """analytic two-bone IK in world space: turn upper arm and forearm so the wrist (hand head) is at target and the
    elbow points towards pole (a world point; default: down and outwards). The hand keeps its pose relative to the forearm."""
    ua, fa, hd = (arm.pose.bones[f'Bip01 {side} {n}'] for n in ('UpperArm', 'Forearm', 'Hand'))
    hd.matrix_basis = Matrix.Identity(4)          # straight wrist (the resting hand of the source pose would point anywhere)
    bpy.context.view_layer.update(); TW = arm.matrix_world
    S, E, W = TW @ ua.head, TW @ fa.head, TW @ hd.head
    a, b = (E - S).length, (W - E).length; T = Vector(target)
    d = T - S; dist = min(d.length, (a + b) * 0.999); dn = d.normalized()
    if pole is None: pole = S + d * 0.5 - Vector((0, 0, 0.5))
    ph = Vector(pole) - S; ph = (ph - dn * ph.dot(dn)).normalized()   # bend direction, perpendicular to the reach
    x = (a * a - b * b + dist * dist) / (2 * dist); h = math.sqrt(max(0.0, a * a - x * x))
    E2 = S + dn * x + ph * h
    _rotate_bone_world(arm, ua, S, (E - S).rotation_difference(E2 - S))
    E1, W1 = TW @ fa.head, TW @ hd.head
    _rotate_bone_world(arm, fa, E1, (W1 - E1).rotation_difference((S + dn * dist) - E1))
    miss = (T - (TW @ hd.head)).length
    print(f"IK {arm.name} {side}: wrist miss {miss:.3f} m (reach {d.length:.2f} of {a + b:.2f})")
