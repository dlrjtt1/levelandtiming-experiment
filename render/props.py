# Objects added to the hall: audience chairs, parquet, PA loudspeakers, orchestra chairs, music stands, instruments.
# Config coordinates: x towards the audience, y to the right as seen from the audience, z up.
import bpy, bmesh, math, os
from mathutils import Vector, Matrix
from PIL import Image, ImageDraw, ImageFilter
import random

def mat(name, color, rough=0.5, metal=0.0, coat=0.0, sheen=0.0, spec=0.5):
    if name in bpy.data.materials: return bpy.data.materials[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat; b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Specular IOR Level"].default_value = spec
    if coat: b.inputs["Coat Roughness"].default_value = 0.35
    if sheen: b.inputs["Sheen Tint"].default_value = (*[min(1, c * 2.2) for c in color], 1); b.inputs["Sheen Roughness"].default_value = 0.35
    return m

def link(o, coll=None):
    (coll or bpy.context.scene.collection).objects.link(o); return o

def box(name, size, loc, m, bevel=0.0, coll=None, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot; me.materials.append(m)
    if bevel:
        bv = o.modifiers.new("bevel", 'BEVEL'); bv.width = bevel; bv.segments = 3; bv.limit_method = 'ANGLE'
    for p in me.polygons: p.use_smooth = True
    return link(o, coll)

def cyl(name, r, length, a, b_dir, m, coll=None, verts=24, r2=None):
    """cylinder of radius r (r2 at the far end) from point a, along direction b_dir"""
    d = Vector(b_dir).normalized()
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r if r2 is None else r2, depth=length)
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); me.materials.append(m)
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    o.location = Vector(a) + d * (length / 2)
    for p in me.polygons: p.use_smooth = True
    return link(o, coll)

def sphere(name, r, loc, m, coll=None, scale=(1, 1, 1)):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=r); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.scale = scale; me.materials.append(m)
    for p in me.polygons: p.use_smooth = True
    return link(o, coll)

def lathe(name, prof, m, loc, coll=None, segs=48, scale=(1, 1, 1)):
    """surface of revolution around z; prof = [(radius, z), ...]"""
    me = bpy.data.meshes.new(name); verts, faces = [], []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        for r, z in prof: verts.append((r * math.cos(a), r * math.sin(a), z))
    n = len(prof)
    for i in range(segs):
        j = (i + 1) % segs
        for k in range(n - 1): faces.append((i * n + k, j * n + k, j * n + k + 1, i * n + k + 1))
    me.from_pydata(verts, [], faces); me.update(); o = bpy.data.objects.new(name, me); o.location = loc; o.scale = scale; me.materials.append(m)
    for p in me.polygons: p.use_smooth = True
    return link(o, coll)

# ---------------------------------------------------------------- audience floor and chairs
def parquet(path):
    """0.6 m squares of diagonal strips, warm brown, as in the BRAS seating photographs; 1024 px = 1.2 m"""
    if os.path.exists(path): return path
    random.seed(3); N = 1024; im = Image.new("RGB", (N, N)); d = ImageDraw.Draw(im)
    for i in range(2):
        for j in range(2):
            x0, y0 = i * 512, j * 512; base = [(140, 74, 42), (150, 82, 46), (128, 66, 38), (156, 88, 50)][(i + 2 * j) % 4]
            tile = Image.new("RGB", (512, 512), base); td = ImageDraw.Draw(tile)
            for k in range(-512, 1024, 34):   # strips
                c = tuple(max(0, min(255, v + random.randint(-14, 14))) for v in base)
                pts = [(k, 0), (k + 34, 0), (k + 34 + 512, 512), (k + 512, 512)] if (i + j) % 2 else [(k, 512), (k + 34, 512), (k + 34 + 512, 0), (k + 512, 0)]
                td.polygon(pts, fill=c, outline=(90, 45, 24))
            noise = Image.effect_noise((512, 512), 18).convert("L").filter(ImageFilter.GaussianBlur(1.2))
            tile = Image.blend(tile, Image.merge("RGB", (noise, noise, noise)), 0.07)
            im.paste(tile, (x0, y0))
    d.rectangle([0, 0, N - 1, N - 1], outline=(165, 125, 90), width=4); d.line([(512, 0), (512, N)], fill=(165, 125, 90), width=4); d.line([(0, 512), (N, 512)], fill=(165, 125, 90), width=4)
    im.save(path, quality=92); return path

def floor_plane(tex_path):
    m = bpy.data.materials.new("parquet"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / 1.2, 1 / 1.2, 1)
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(tex_path)
    nt.links.new(tc.outputs["Object"], mp.inputs[0]); nt.links.new(mp.outputs[0], tx.inputs[0]); nt.links.new(tx.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.35; b.inputs["Coat Weight"].default_value = 0.3; b.inputs["Coat Roughness"].default_value = 0.2
    me = bpy.data.meshes.new("floor"); me.from_pydata([(-0.75, -6.9, 0), (16.0, -6.9, 0), (16.0, 6.9, 0), (-0.75, 6.9, 0)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("audience_floor", me); o.location.z = 0.003; me.materials.append(m); return link(o)

def rail(name, pts, r, m, coll, res=6):
    """round rail through points (a bevelled curve), converted to a mesh"""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 3; cu.resolution_u = res
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts): bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    cu.use_fill_caps = True
    o = bpy.data.objects.new(name, cu); cu.materials.append(m); coll.objects.link(o); return o

def audience_chair_collection():
    """one chair, front towards -x, after the BRAS photographs (seating close-up and the 360° photo seen from behind):
    thin ivory painted frame, square back with a flat top rail and small knobs on the post tops, large blue-green velvet
    back panel, flat armrests ending in a scroll, seat folded up (empty hall). Chairs 0.571 m apart (spacing chosen
    by the user on 2026-11-25)."""
    c = bpy.data.collections.new("chair"); ivory = mat("ivory_paint", (0.56, 0.52, 0.44), 0.45, coat=0.15)
    velvet = mat("velvet", (0.025, 0.05, 0.06), 0.85, sheen=0.7, spec=0.2)
    bx = 0.21; B = 0.006                                        # plane of the back, bevel
    box("back_panel", (0.03, 0.47, 0.43), (bx + 0.004, 0, 0.665), velvet, 0.01, c)
    box("top_rail", (0.035, 0.53, 0.04), (bx, 0, 0.90), ivory, B, c)
    box("mid_rail", (0.035, 0.50, 0.035), (bx, 0, 0.44), ivory, B, c)
    box("low_rail", (0.03, 0.50, 0.03), (bx, 0, 0.26), ivory, B, c)
    box("folded_seat", (0.07, 0.44, 0.40), (0.12, 0, 0.52), velvet, 0.018, c)
    box("seat_edge", (0.072, 0.442, 0.016), (0.12, 0, 0.726), ivory, 0.004, c)
    for s in (-1, 1):
        y = 0.25 * s
        box("back_post", (0.04, 0.04, 0.92), (bx, y, 0.46), ivory, B, c)
        sphere("knob", 0.022, (bx, y, 0.935), ivory, c)
        box("arm", (0.48, 0.05, 0.03), (-0.02, 0.28 * s, 0.64), ivory, B, c)
        cyl("arm_scroll", 0.024, 0.05, (-0.26, 0.28 * s - 0.025, 0.625), (0, 1, 0), ivory, c)
        box("arm_support", (0.04, 0.04, 0.36), (-0.21, 0.28 * s, 0.44), ivory, B, c)
        box("front_leg", (0.04, 0.04, 0.27), (-0.21, 0.28 * s, 0.135), ivory, B, c)
        box("side_rail", (0.40, 0.03, 0.04), (0.0, 0.27 * s, 0.26), ivory, B, c)
        for x in (-0.21, bx):
            box("foot_cap", (0.045, 0.045, 0.025), (x, (0.28 if x < 0 else 0.25) * s, 0.0125), mat("foot_cap", (0.08, 0.06, 0.04), 0.5, metal=0.4), 0.004, c)
    return c

def audience_chairs(ear_x):
    col = audience_chair_collection()   # not linked to the scene: used only through instances
    places = []
    for k in range(0, 13):
        rx = ear_x - 0.05 - k * 0.92
        if rx < 1.9: break
        for j in range(15): places.append((rx, -4 + j * 8 / 14))
    for k in range(1, 4):   # a few rows behind the listener (for the light bouncing around)
        for j in range(15): places.append((ear_x - 0.05 + k * 0.92, -4 + j * 8 / 14))
    for i, (px, py) in enumerate(places):
        o = bpy.data.objects.new(f"chair_{i}", None); o.instance_type = 'COLLECTION'; o.instance_collection = col; o.location = (px, py, 0); link(o)
    return places

# ---------------------------------------------------------------- PA loudspeakers (assumed; CR3 has none)
def pa_speaker(pos, aim):
    p, a = Vector(pos), Vector(aim); blk = mat("speaker_black", (0.02, 0.02, 0.022), 0.45); grille = mat("grille", (0.05, 0.05, 0.055), 0.8, metal=0.3)
    d = (a - p); yaw = math.atan2(d.y, d.x); pitch = math.atan2(d.z, d.xy.length)
    cab = box("pa_cabinet", (0.30, 0.30, 0.48), p, blk, 0.02); cab.rotation_euler = (0, -pitch, yaw)
    g = box("pa_grille", (0.01, 0.27, 0.44), p + Vector((math.cos(yaw), math.sin(yaw), 0)) * 0.152, grille, 0.004); g.rotation_euler = (0, -pitch, yaw)
    metal = mat("stand_metal", (0.03, 0.03, 0.03), 0.4, metal=0.8)
    cyl("pa_pole", 0.018, p.z - 0.24, (p.x, p.y, 0), (0, 0, 1), metal, verts=16)
    for k in range(3):
        ang = 2 * math.pi * k / 3 + 0.4
        foot = Vector((p.x + 0.42 * math.cos(ang), p.y + 0.42 * math.sin(ang), 0.0)); top = Vector((p.x, p.y, 0.62))
        cyl("pa_leg", 0.012, (top - foot).length, foot, top - foot, metal, verts=10)

# ---------------------------------------------------------------- orchestra furniture
def orchestra_chair(base, yaw):
    blk = mat("orch_chair", (0.015, 0.015, 0.017), 0.5); R = Matrix.Rotation(yaw, 4, 'Z')
    def P(x, y, z): return Vector(base) + (R @ Vector((x, y, z)))
    s = box("oc_seat", (0.44, 0.44, 0.06), P(0, 0, 0.45), blk, 0.015); s.rotation_euler.z = yaw
    b = box("oc_back", (0.05, 0.42, 0.36), P(-0.22, 0, 0.72), blk, 0.015); b.rotation_euler = (0, -0.12, yaw)
    for dx, dy in ((-0.19, -0.19), (-0.19, 0.19), (0.19, -0.19), (0.19, 0.19)):
        cyl("oc_leg", 0.014, 0.43, P(dx, dy, 0), (0, 0, 1), mat("chrome", (0.6, 0.6, 0.62), 0.2, metal=1.0), verts=10)

def music_stand(base, yaw, height=1.05):
    blk = mat("stand_black", (0.02, 0.02, 0.02), 0.45, metal=0.5); paper = mat("paper", (0.85, 0.83, 0.78), 0.8)
    R = Matrix.Rotation(yaw, 4, 'Z'); b = Vector(base)
    cyl("ms_pole", 0.012, height - 0.1, b, (0, 0, 1), blk, verts=10)
    desk = box("ms_desk", (0.012, 0.5, 0.34), b + Vector((0, 0, height)), blk, 0.003); desk.rotation_euler = (0, math.radians(-25), yaw)
    sh = box("ms_sheet", (0.004, 0.46, 0.31), b + (R @ Vector((0.012, 0, 0))) + Vector((0, 0, height + 0.012)), paper); sh.rotation_euler = (0, math.radians(-25), yaw)
    for k in range(3):
        ang = yaw + 2 * math.pi * k / 3
        cyl("ms_leg", 0.008, 0.33, b + Vector((0, 0, 0.2)), (math.cos(ang) * 0.3, math.sin(ang) * 0.3, -0.2), blk, verts=8)

# ---------------------------------------------------------------- instruments
def _orient(o, origin, axis, up_hint):
    """local +y -> axis, local +z -> as close to up_hint as possible"""
    y = Vector(axis).normalized(); z = (Vector(up_hint) - y * Vector(up_hint).dot(y)).normalized(); x = y.cross(z)
    M = Matrix(((x[0], y[0], z[0], 0), (x[1], y[1], z[1], 0), (x[2], y[2], z[2], 0), (0, 0, 0, 1)))
    o.matrix_world = Matrix.Translation(Vector(origin)) @ M @ Matrix.Diagonal((*o.scale, 1))

def _violin_outline(length, n=60):
    ctrl = [(0.0, 0.10), (0.04, 0.22), (0.12, 0.285), (0.24, 0.29), (0.36, 0.25), (0.45, 0.17), (0.5, 0.165), (0.56, 0.18),
            (0.64, 0.225), (0.76, 0.24), (0.88, 0.21), (0.96, 0.14), (1.0, 0.06)]
    def hw(t):
        for (t0, w0), (t1, w1) in zip(ctrl, ctrl[1:]):
            if t0 <= t <= t1:
                u = (t - t0) / (t1 - t0); u = u * u * (3 - 2 * u); return (w0 + (w1 - w0) * u) * length
        return 0.0
    ts = [0.5 - 0.5 * math.cos(math.pi * i / n) for i in range(n + 1)]
    right = [(hw(t), t * length) for t in ts]; left = [(-w, y) for w, y in reversed(right[1:-1])]
    return right + left

def string_instrument(name, body_len, rib, neck_len, origin, axis, up_hint, wood=None):
    """body from origin along axis (tail at origin), top plate facing up_hint"""
    wood = wood or mat("varnish", (0.12, 0.04, 0.012), 0.55, coat=0.1, spec=0.3)
    ebony = mat("ebony", (0.01, 0.008, 0.007), 0.3, coat=0.3)
    parts = []
    pts = _violin_outline(body_len); me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((x, y, 0)) for x, y in pts]; f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f]); top = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    for v in top: v.co.z = rib
    bm.normal_update(); bm.to_mesh(me); bm.free()
    body = bpy.data.objects.new(name + "_body", me); me.materials.append(wood); link(body)
    bv = body.modifiers.new("bevel", 'BEVEL'); bv.width = rib * 0.3; bv.segments = 4
    for p in me.polygons: p.use_smooth = True
    parts.append(body)
    fb = box(name + "_fingerboard", (body_len * 0.13, neck_len * 1.0, rib * 0.25), (0, body_len * 0.72 + neck_len * 0.25, rib * 1.35), ebony, rib * 0.05); parts.append(fb)
    nk = box(name + "_neck", (body_len * 0.1, neck_len * 0.62, rib * 0.6), (0, body_len + neck_len * 0.3, rib * 0.7), wood, rib * 0.1); parts.append(nk)
    sc = sphere(name + "_scroll", body_len * 0.06, (0, body_len + neck_len * 0.68, rib * 0.8), wood, scale=(0.8, 1.4, 1.0)); parts.append(sc)
    tp = box(name + "_tailpiece", (body_len * 0.1, body_len * 0.2, rib * 0.15), (0, body_len * 0.12, rib * 1.08), ebony, rib * 0.04); parts.append(tp)
    br = box(name + "_bridge", (body_len * 0.12, body_len * 0.012, rib * 0.6), (0, body_len * 0.42, rib * 1.25), mat("maple", (0.75, 0.6, 0.4), 0.5)); parts.append(br)
    root = bpy.data.objects.new(name, None); link(root)
    for p in parts: p.parent = root
    _orient(root, origin, axis, up_hint)
    return root

def bow(a, b):
    stick = mat("pernambuco", (0.12, 0.05, 0.02), 0.3, coat=0.5); hair = mat("bow_hair", (0.85, 0.82, 0.72), 0.6)
    a, b = Vector(a), Vector(b); d = b - a
    cyl("bow_stick", 0.004, d.length, a, d, stick, verts=8)
    off = d.orthogonal().normalized() * 0.012
    cyl("bow_hair", 0.002, d.length * 0.95, a + off, d, hair, verts=6)

def tube(name, a, b, r, m, r2=None):
    a, b = Vector(a), Vector(b); return cyl(name, r, (b - a).length, a, b - a, m, r2=r2)

def flute(a, d):
    silver = mat("silver", (0.85, 0.85, 0.86), 0.12, metal=1.0); tube("flute", a, Vector(a) + Vector(d).normalized() * 0.67, 0.0095, silver)

def clarinet(a, d):
    gren = mat("grenadilla", (0.015, 0.012, 0.012), 0.25, coat=0.6); d = Vector(d).normalized(); a = Vector(a)
    tube("clarinet", a, a + d * 0.6, 0.013, gren, r2=0.015); tube("clarinet_bell", a + d * 0.6, a + d * 0.67, 0.015, gren, r2=0.034)

def bassoon(base, axis, mouth):
    maple = mat("bassoon_wood", (0.30, 0.09, 0.03), 0.25, coat=0.7); silver = mat("silver", (0.85, 0.85, 0.86), 0.12, metal=1.0)
    base = Vector(base); ax = Vector(axis).normalized()
    tube("bassoon_long", base, base + ax * 1.30, 0.021, maple); side = ax.orthogonal().normalized() * 0.045
    tube("bassoon_wing", base + side, base + side + ax * 0.62, 0.018, maple); tube("bassoon_boot", base - ax * 0.05, base + side - ax * 0.05, 0.03, maple)
    tube("bocal", base + side + ax * 0.62, Vector(mouth), 0.004, silver)

def horn(center, facing, bell_dir):
    brass = mat("brass", (0.85, 0.62, 0.25), 0.18, metal=1.0); c = Vector(center)
    me = bpy.data.meshes.new("horn_coil"); bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=False, segments=48, radius=0.15); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("horn_coil", me); link(o); me.materials.append(brass)
    sk = o.modifiers.new("skin", 'SKIN'); [setattr(v, "radius", (0.012, 0.012)) for v in me.skin_vertices[0].data]
    o.modifiers.new("sub", 'SUBSURF').levels = 1
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector(facing)); o.location = c
    bd = Vector(bell_dir).normalized(); start = c + bd * 0.12
    prof = [(0.018, 0.0), (0.03, 0.12), (0.06, 0.2), (0.15, 0.27), (0.16, 0.275)]
    b = lathe("horn_bell", prof, brass, start); b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(bd)
    b.data.materials[0] = brass
    return o

# real-proportion violin family (replaces the flat placeholder above)
from strings_model import string_instrument  # noqa: E402,F811
from winds_model import flute, clarinet, bassoon, horn  # noqa: E402,F811
